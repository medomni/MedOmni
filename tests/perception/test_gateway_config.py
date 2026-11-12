"""Deployment validation (the workspace's `deployment` mapping, R-60). An effective value must be the value written."""
import tempfile
import unittest
from pathlib import Path


from medomni.perception.gateway import config


def written(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    handle.write(text)
    handle.close()
    return handle.name


V02_DEPLOYMENT = {  # v0.2's perception/deployment.yaml, as a workspace's deployment mapping
    "data_root": None, "max_live_containers": 5, "idle_timeout_s": 900, "reap_interval_s": 30,
    "start_timeout_s": 180, "acquire_timeout_s": 300, "encode_timeout_s": 600, "default_concurrency": 4,
    "image_tag": "dev", "bind_host": "127.0.0.1", "cache_bytes": 268435456, "call_log": "var/calls.jsonl",
    "log_paths": True, "stop_on_exit": True, "container_prefix": "medomni-gw", "admin_api": True,
    "encoders": {"ecg-12lead-500hz-mv__ecgfounder": {"concurrency": 1},
                 "cxr-radiograph-2d__torchxrayvision": {"concurrency": 2}},
}


class ConfigTests(unittest.TestCase):
    def test_v02_deployment_is_valid_as_a_workspace_mapping(self):
        loaded = config.from_mapping(V02_DEPLOYMENT, Path(tempfile.gettempdir()))
        self.assertEqual(5, loaded.max_live_containers)
        self.assertEqual(1, loaded.concurrency("ecg-12lead-500hz-mv__ecgfounder"))
        self.assertEqual(Path(tempfile.gettempdir()) / "var/calls.jsonl", loaded.call_log)

    def test_the_encoder_set_may_be_a_list_of_ids(self):
        loaded = config.from_mapping({"encoders": ["a__b", "c__d"]}, Path.cwd())
        self.assertEqual({"a__b": {}, "c__d": {}}, loaded.encoders)
        self.assertEqual(4, loaded.concurrency("a__b"))
        with self.assertRaises(config.ConfigError):
            config.from_mapping({"encoders": ["a__b", "a__b"]}, Path.cwd())

    def test_from_workspace_reads_the_deployment_field(self):
        from medomni.core.contracts import WorkspaceConfig, load_data

        with tempfile.TemporaryDirectory() as home:
            cfg = load_data({"cache": f"{home}/cache", "tasks": f"{home}/tasks", "runs": f"{home}/runs",
                             "results": f"{home}/results.jsonl",
                             "deployment": {"max_live_containers": 2, "call_log": None}}, WorkspaceConfig)
            self.assertEqual(2, config.from_workspace(cfg).max_live_containers)

    def test_fractional_counts_are_rejected(self):
        for text in ("max_live_containers: 0.5\n", "cache_bytes: 0.5\n",
                     "default_concurrency: 1.5\n",
                     "encoders: {a__b: {concurrency: 1.5}}\n"):
            with self.subTest(text=text.strip()):
                with self.assertRaises(config.ConfigError):
                    config.load(written(text))

    def test_the_encode_timeout_is_the_value_written(self):
        """It decides when the pool removes a container that is still working."""
        self.assertEqual(90.0, config.load(written("encode_timeout_s: 90\n")).encode_timeout_s)

    def test_zero_and_negative_counts_are_rejected(self):
        for text in ("max_live_containers: 0\n", "default_concurrency: 0\n",
                     "cache_bytes: -1\n", "start_timeout_s: 0\n",
                     "encode_timeout_s: 0\n", "encode_timeout_s: -1\n"):
            with self.subTest(text=text.strip()):
                with self.assertRaises(config.ConfigError):
                    config.load(written(text))

    def test_a_string_is_not_a_boolean(self):
        for text in ('stop_on_exit: "false"\n', "log_paths: 1\n"):
            with self.subTest(text=text.strip()):
                with self.assertRaises(config.ConfigError):
                    config.load(written(text))

    def test_zero_disables_rather_than_being_invalid(self):
        loaded = config.load(written("idle_timeout_s: 0\ncache_bytes: 0\n"))
        self.assertEqual(0.0, loaded.idle_timeout_s)
        self.assertEqual(0, loaded.cache_bytes)

    def test_a_missing_data_root_is_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.load(written("data_root: /no/such/directory\n"))

    def test_unknown_keys_are_rejected(self):
        with self.assertRaises(config.ConfigError):
            config.load(written("device: cuda\n"))
        with self.assertRaises(config.ConfigError):
            config.load(written("encoders: {a__b: {replicas: 2}}\n"))

    def test_unsafe_names_are_rejected(self):
        for text in ("container_prefix: 'bad name'\n", "image_tag: ''\n",
                     "bind_host: ''\n"):
            with self.subTest(text=text.strip()):
                with self.assertRaises(config.ConfigError):
                    config.load(written(text))

    def test_per_encoder_concurrency_overrides_the_default(self):
        loaded = config.load(written(
            "default_concurrency: 4\nencoders:\n  a__b:\n    concurrency: 1\n"))
        self.assertEqual(1, loaded.concurrency("a__b"))
        self.assertEqual(4, loaded.concurrency("c__d"))


if __name__ == "__main__":
    unittest.main()
