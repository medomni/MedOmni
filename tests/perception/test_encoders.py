"""The 44 shipped encoders (R-63, R-66, R-117): one test for every folder, in place of v0.2's per-folder verify.py.

T1, with no Docker: each card validates; each adapter declares the family its card reads; test data and
`expected.json` are where v0.2 kept them; the Dockerfile builds the v0.3 layout; asset manifests pin the card's
checkpoint; and the hand-calculated oracles (v0.2's verify.py, one function each below) pass with the adapter run
in-process. T2 (`containers`): each built image answers its test data as `expected.json` says.
"""
import ast
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from medomni.core.contracts import ModelCard, load
from tests.repro.migrate.cards import shipped

REPO = Path(__file__).resolve().parents[2]
ENCODERS = REPO / "perception/encoders"
SHIPPED = shipped(REPO)
GHCR = "ghcr.io/medomni"
RUNTIME_COPIES = ("COPY src/medomni/__init__.py medomni/", "COPY src/medomni/core medomni/core",
                  "COPY src/medomni/perception/__init__.py medomni/perception/",
                  "COPY src/medomni/perception/runtime medomni/perception/runtime", "COPY core/families core/families")


def folder(eid):
    return ENCODERS / eid.replace("__", "/", 1)


def _finite(value, path="response"):
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: value must be finite"]
    if isinstance(value, dict):
        return [e for k, v in value.items() for e in _finite(v, f"{path}.{k}")]
    if isinstance(value, list):
        return [e for i, v in enumerate(value) for e in _finite(v, f"{path}[{i}]")]
    return []


def conforms(card, response):
    """The output facts a card promises for every real sample (v0.2's registry.validate_family_response)."""
    errors = []
    if not isinstance(response, dict):
        return ["response is not an object"]
    if response.get("encoder_id") != card["id"]:
        errors.append("response encoder_id does not match the card")
    if response.get("family") != card["family"]:
        errors.append("response family does not match the card")
    if response.get("healthy") is not True:
        errors.append("real family sample did not produce healthy output")
    outputs = response.get("outputs")
    if not isinstance(outputs, list):
        return errors + ["response outputs is not a list"]
    declarations = card.get("outputs") or []
    if len(outputs) != len(declarations):
        errors.append(f"card declares {len(declarations)} output block(s), got {len(outputs)}")
    for index, block in enumerate(outputs):
        if not isinstance(block, dict):
            errors.append(f"output {index} is not an object")
            continue
        declaration = declarations[index] if index < len(declarations) else {}
        if block.get("kind") != declaration.get("kind"):
            errors.append(f"output {index} kind does not match the card")
        if block.get("kind") == "embedding" and block.get("dim") != declaration.get("dim"):
            errors.append(f"output {index} embedding dimension does not match the card")
        if block.get("kind") in ("labels", "events"):
            declared = set(declaration.get("labels") or [])
            emitted = {item.get("label") for item in block.get("items") or [] if isinstance(item, dict)}
            if unknown := sorted(emitted - declared):
                errors.append(f"output {index} has undeclared labels: {', '.join(unknown)}")
    return errors + _finite(response)


def _options(edir, name):
    p = edir / "family-test.json"
    if not p.exists():
        return {}
    config = json.loads(p.read_text())
    default, override = config.get("default", {}), config.get("samples", {}).get(name, {})
    options = dict(default.get("options", default))
    options.update(override.get("options", override))
    return options


def run_case(edir):
    """Every testdata/input* sample through the adapter in-process. Returns the card and {file: response}."""
    from medomni.perception.runtime import load_adapter, load_card
    from medomni.perception.runtime.serve import run_encode

    card = load_card(edir / "card.yaml")
    adapter = load_adapter(edir / "adapter.py")
    model = adapter.load() if hasattr(adapter, "load") else None
    inputs = sorted(p.name for p in (edir / "testdata").glob("input*") if p.is_file())
    results = {}
    for name in inputs:
        body = {"family": card["family"], "path": name, "options": _options(edir, name)}
        r = run_encode(card, adapter, body, data_root=str(edir / "testdata"), model=model)
        r.pop("runtime", None)
        results[name] = r
    return card, results


def _v02_files():
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "perception/encoders"], capture_output=True, text=True,
                         check=True).stdout.split()
    return set(out)


# ---------------------------------------------------------------- T1: every shipped folder

def test_44_encoders_ship():
    assert len(SHIPPED) == 44


@pytest.mark.parametrize("eid", SHIPPED)
def test_card_validates(eid):
    card = load(folder(eid) / "card.yaml", ModelCard)
    assert card.id == eid and card.authors


@pytest.mark.parametrize("eid", SHIPPED)
def test_adapter_reads_the_cards_family(eid):
    tree = ast.parse((folder(eid) / "adapter.py").read_text())
    family = next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                  and any(getattr(t, "id", None) == "FAMILY" for t in n.targets))
    encode = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "encode")
              or (isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "encode" for t in n.targets))]
    assert family == yaml.safe_load((folder(eid) / "card.yaml").read_text())["family"] and encode
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "contract" not in imports  # the v0.2 runtime module is gone (R-117)


@pytest.mark.parametrize("eid", SHIPPED)
def test_test_data_is_kept(eid):
    edir = folder(eid)
    assert any((edir / "testdata").glob("input*"))
    if f"{edir.relative_to(REPO)}/testdata/expected.json" in _v02_files():
        assert json.loads((edir / "testdata/expected.json").read_text())


@pytest.mark.parametrize("eid", SHIPPED)
def test_dockerfile_builds_the_v03_layout(eid):
    edir = folder(eid)
    rel = edir.relative_to(REPO).as_posix()
    lines = [l.strip() for l in (edir / "Dockerfile").read_text().splitlines()]
    assert all(c in lines for c in RUNTIME_COPIES)
    assert lines[-1] == 'CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]'
    env = next(l for l in reversed(lines) if l.startswith("ENV "))
    assert "PYTHONPATH=/app" in env and "MEDOMNI_ROOT=/app" in env
    copied = [l for l in lines if l.startswith("COPY ") and "--from=" not in l]
    assert any(f"{rel}/adapter.py" in l for l in copied) and any(f"{rel}/card.yaml" in l for l in copied)
    assert any(f"{rel}/testdata" in l for l in copied)
    assert not any(" encoders/" in l or "runtime/contract.py" in l or "prepare_assets.py" in l for l in lines)
    ignore = (edir / "Dockerfile.dockerignore").read_text().splitlines()
    for l in copied:
        for src in l.split()[1:-1]:
            assert f"!{src}" in ignore, src


@pytest.mark.parametrize("eid", [e for e in SHIPPED if (folder(e) / "assets.json").exists()])
def test_asset_manifest_pins_the_cards_checkpoint(eid):
    from medomni.perception.runtime.assets import manifest

    items = manifest(folder(eid))
    card = yaml.safe_load((folder(eid) / "card.yaml").read_text())
    for item in items:
        if item.get("weights"):
            assert item["sha256"] == card["weights"]["sha256"], item["path"]
    assert not (folder(eid) / "prepare_assets.py").exists()  # one asset step (R-117)


# ---------------------------------------------------------------- T1: hand-calculated oracles (v0.2's verify.py)


def _body_position_code_10hz_rule_occupancy(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["code_count"] == 2
    assert values["modal_fraction"] == 0.5
    assert values["code_entropy"] == 1
    assert values["transition_count"] == 39
    assert values["duration"] == 4
    assert not conforms(card, response)


def _emg_chin_200hz_uv_rule_amplitude(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert abs(values["chin1_chin2_mean"]) < 1e-10
    assert abs(values["chin1_chin2_rms"] - 10) < 1e-10
    assert values["chin1_chin2_peak_to_peak"] == 20
    assert values["chin1_chin2_duration"] == 4
    assert not conforms(card, response)


def _emg_limb_200hz_uv_rule_amplitude(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert len(values) == 20
    assert abs(values["leg_left_mean"]) < 1e-10
    assert abs(values["leg_left_rms"] - 10) < 1e-10
    assert values["arm_right_duration"] == 4
    assert not conforms(card, response)


def _flio_tcspc_256x256x1024bin_u16_rule_photons(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["photon_count"] == 4*256*256
    assert values["mean_arrival_bin"] == 15
    assert values["std_arrival_bin"] == 5
    assert values["peak_bin"] == 10
    assert values["nonzero_pixel_fraction"] == 1
    assert not conforms(card, response)


def _fundus_faf_mono8_2d_rule_intensity(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["intensity_mean"] == 50
    assert values["intensity_std"] == 50
    assert values["intensity_entropy"] == 1
    assert values["zero_fraction"] == 0.5
    assert values["saturated_fraction"] == 0
    assert values["frame_count"] == 1
    assert not conforms(card, response)


def _oct_bscanset_radial24_circle3_mono8_rule_intensity(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["intensity_mean"] == 50
    assert values["intensity_std"] == 50
    assert values["intensity_entropy"] == 1
    assert values["zero_fraction"] == 0.5
    assert values["saturated_fraction"] == 0
    assert values["frame_count"] == 27
    assert not conforms(card, response)


def _oct_volume_raster_mono8_3d_rule_intensity(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["intensity_mean"] == 50
    assert values["intensity_std"] == 50
    assert values["intensity_entropy"] == 1
    assert values["zero_fraction"] == 0.5
    assert values["saturated_fraction"] == 0
    assert values["frame_count"] == 3
    assert not conforms(card, response)


def _octa_enface_slab_mono8_2d_rule_intensity(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["intensity_mean"] == 50
    assert values["intensity_std"] == 50
    assert values["intensity_entropy"] == 1
    assert values["zero_fraction"] == 0.5
    assert values["saturated_fraction"] == 0
    assert values["frame_count"] == 1
    assert not conforms(card, response)


def _octa_enface_slab_mono8_2d_vessel_density(card, results):
    """Independent expectations for the synthetic fixtures; run before freezing.

The fixture FAZ is a disc of radius 0.3 mm at the scan centre: area pi * 0.09 = 0.2827 mm2."""
    for name in ("input.dcm", "input-unidentified.dcm"):
        response = results[name]
        assert response["healthy"], response
        values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
        assert abs(values["faz_area_mm2"] - math.pi * 0.09) < 0.02, values
        assert values["fovea_offset_mm"] < 0.03, values
        assert 0 < values["parafovea_vessel_density"] < 1, values
        assert not conforms(card, response)
    assert any("not identified as superficial" in n for n in results["input-unidentified.dcm"]["notes"])
    disc = results["input-disc.dcm"]
    assert disc["healthy"] and not disc["outputs"][0]["items"] and "not apply" in disc["outputs"][2]["text"], disc
    assert not results["input-unknown.dcm"]["healthy"]


def _octa_flowcube_mono8_3d_rule_intensity(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["intensity_mean"] == 50
    assert values["intensity_std"] == 50
    assert values["intensity_entropy"] == 1
    assert values["zero_fraction"] == 0.5
    assert values["saturated_fraction"] == 0
    assert values["frame_count"] == 3
    assert not conforms(card, response)


def _pressure_nonarterial_125hz_mmhg_rule_summary(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    assert not results["input-empty.hea"]["healthy"]
    for name in ("input.hea", "input-frames.hea", "input-artifact.hea"):
        assert results[name]["healthy"], results[name]
        assert not conforms(card, results[name])
    value = lambda name: {i["label"]: i["value"] for i in results[name]["outputs"][0]["items"]}
    cvp = value("input.hea")  # alternating 6 and 10 mmHg
    assert abs(cvp["cvp_median"] - 8) < 1e-9 and abs(cvp["cvp_std"] - 2) < 1e-9
    assert cvp["cvp_implausible_fraction"] == 0 and cvp["cvp_valid_fraction"] == 1
    assert abs(cvp["cvp_duration"] - 1000 / 124.945) < 1e-9
    pap = value("input-frames.hea")  # 500 frames x 2 samples: expanded, not averaged to 20
    assert abs(pap["pap_std"] - 10) < 1e-9 and abs(pap["pap_duration"] - 1000 / 124.945) < 1e-9
    assert not any(k.startswith("ii_") for k in pap)
    art = value("input-artifact.hea")  # held at 398 mmHg
    assert art["cvp_implausible_fraction"] == 1
    assert any("unzeroed transducer" in n for n in results["input-artifact.hea"]["notes"])


def _pulse_rate_10hz_bpm_rule_summary(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["pulse_mean"] == 80
    assert values["pulse_std"] == 20
    assert values["duration"] == 4
    assert values["valid_fraction"] == 1
    assert not conforms(card, response)


def _resp_flow_rule_amplitude(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert abs(values["nasal_pressure_mean"]) < 1e-10
    assert abs(values["nasal_pressure_rms"] - 10) < 1e-10
    assert values["nasal_pressure_duration"] == 4
    assert not conforms(card, response)


def _resp_impedance_62hz_ohm_rule_amplitude(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.hea"]
    assert response["healthy"], response
    assert not results["input-empty.hea"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert abs(values["resp_mean"]) < 1e-3
    assert abs(values["resp_rms"] - 10) < 1e-3
    assert abs(values["resp_duration"] - 250/62.4725) < 1e-9
    assert not conforms(card, response)


def _retinal_heightmap_surfaces_f32_layer_thickness(card, results):
    """Independent analytic expectations for the synthetic fixtures; run before freezing.

Pit: thickness(r) = 75 - 23 exp(-r^2 / 2s^2) px, s = 0.35 mm. Its mean over an annulus R1..R2 is
75 - 23 (2s^2 / (R2^2 - R1^2)) (exp(-R1^2/2s^2) - exp(-R2^2/2s^2))."""
    def ring(r1, r2, s=0.35):
        return 75 - 23 * (2 * s * s / (r2 * r2 - r1 * r1)) * (math.exp(-r1 * r1 / (2 * s * s)) - math.exp(-r2 * r2 / (2 * s * s)))


    for name, axial in (("input.dcm", 3.872), ("input-topcon.dcm", 2.6)):
        response = results[name]
        assert response["healthy"], response
        values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
        for region, r1, r2 in (("center", 0, 0.5), ("inner", 0.5, 1.5), ("outer", 1.5, 3.0)):
            expected = ring(r1, r2) * axial
            assert abs(values[f"thickness_{region}_um"] - expected) < 1.0, (name, region, values, expected)
        assert abs(values["gcipl_outer_um"] - 20 * axial) < 0.2, (name, values)
        assert values["fovea_offset_mm"] < 0.051, values
        assert not conforms(card, response)
    assert any("anatomical depth order" in n for n in results["input-topcon.dcm"]["notes"])
    disc = results["input-disc.dcm"]
    assert disc["healthy"] and not disc["outputs"][0]["items"] and "does not apply" in disc["outputs"][2]["text"], disc
    assert not results["input-empty.dcm"]["healthy"]


def _retinal_heightmap_surfaces_f32_rule_surfaces(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.dcm"]
    assert response["healthy"], response
    assert not results["input-empty.dcm"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["surface_count"] == 2
    assert values["surface_0_mean"] == 50
    assert values["surface_1_range"] == 100
    assert not conforms(card, response)


def _snore_acoustic_rule_amplitude(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.edf"]
    assert response["healthy"], response
    assert not results["input-empty.edf"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert abs(values["snore_mean"]) < 1e-10
    assert abs(values["snore_rms"] - 10) < 1e-10
    assert values["snore_duration"] == 4
    assert not conforms(card, response)


def _wearable_spo2_1min_pct_rule_summary(card, results):
    """Independent hand-calculated fixture expectations; run before freezing."""
    response = results["input.json"]
    assert response["healthy"], response
    assert not results["input-empty.json"]["healthy"]
    values = {i["label"]: i["value"] for i in response["outputs"][0]["items"]}
    assert values["spo2_mean"] == 95
    assert values["excluded_count"] == 1
    assert values["valid_count"] == 3
    assert not conforms(card, response)


ORACLES = {
    "body-position-code-10hz__rule-occupancy": _body_position_code_10hz_rule_occupancy,
    "emg-chin-200hz-uv__rule-amplitude": _emg_chin_200hz_uv_rule_amplitude,
    "emg-limb-200hz-uv__rule-amplitude": _emg_limb_200hz_uv_rule_amplitude,
    "flio-tcspc-256x256x1024bin-u16__rule-photons": _flio_tcspc_256x256x1024bin_u16_rule_photons,
    "fundus-faf-mono8-2d__rule-intensity": _fundus_faf_mono8_2d_rule_intensity,
    "oct-bscanset-radial24-circle3-mono8__rule-intensity": _oct_bscanset_radial24_circle3_mono8_rule_intensity,
    "oct-volume-raster-mono8-3d__rule-intensity": _oct_volume_raster_mono8_3d_rule_intensity,
    "octa-enface-slab-mono8-2d__rule-intensity": _octa_enface_slab_mono8_2d_rule_intensity,
    "octa-enface-slab-mono8-2d__vessel-density": _octa_enface_slab_mono8_2d_vessel_density,
    "octa-flowcube-mono8-3d__rule-intensity": _octa_flowcube_mono8_3d_rule_intensity,
    "pressure-nonarterial-125hz-mmhg__rule-summary": _pressure_nonarterial_125hz_mmhg_rule_summary,
    "pulse-rate-10hz-bpm__rule-summary": _pulse_rate_10hz_bpm_rule_summary,
    "resp-flow__rule-amplitude": _resp_flow_rule_amplitude,
    "resp-impedance-62hz-ohm__rule-amplitude": _resp_impedance_62hz_ohm_rule_amplitude,
    "retinal-heightmap-surfaces-f32__layer-thickness": _retinal_heightmap_surfaces_f32_layer_thickness,
    "retinal-heightmap-surfaces-f32__rule-surfaces": _retinal_heightmap_surfaces_f32_rule_surfaces,
    "snore-acoustic__rule-amplitude": _snore_acoustic_rule_amplitude,
    "wearable-spo2-1min-pct__rule-summary": _wearable_spo2_1min_pct_rule_summary,
}


@pytest.mark.parametrize("eid", sorted(ORACLES))
def test_oracle(eid, monkeypatch):
    """The adapter, run in-process on its test data, gives the hand-calculated values."""
    monkeypatch.syspath_prepend(str(folder(eid)))  # an adapter's sibling modules (norms.py), as /app is in the image
    for sibling in folder(eid).glob("*.py"):  # two adapters each have their own norms.py; never share a cached one
        monkeypatch.delitem(sys.modules, sibling.stem, raising=False)
    card, results = run_case(folder(eid))
    ORACLES[eid](card, results)


# ---------------------------------------------------------------- T2: the built image

@pytest.mark.containers
@pytest.mark.parametrize("eid", SHIPPED)
def test_image_answers_as_expected(eid):
    """The :dev image, run on the test data it carries, gives expected.json (runtime fields aside)."""
    edir = folder(eid)
    expected_file = edir / "testdata/expected.json"
    if not expected_file.exists():
        pytest.skip("no expected.json")
    expected = json.loads(expected_file.read_text())
    card = yaml.safe_load((edir / "card.yaml").read_text())
    for name, want in expected.items():
        r = subprocess.run(["docker", "run", "--rm", "--network", "none", f"{GHCR}/{eid}:dev", "python", "-m",
                            "medomni.perception.runtime.serve", "encode", "--family", card["family"], "--path", name,
                            "--data-root", "/app/testdata", "--options-json", json.dumps(_options(edir, name))],
                           capture_output=True, text=True, timeout=1800)
        assert r.returncode == 0, r.stderr[-2000:]
        got = json.loads(r.stdout)
        got.pop("runtime", None)
        want = dict(want)
        want.pop("runtime", None)
        assert got == want, name
