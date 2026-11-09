"""The one Docker runner (R-117): start an encoder image, adopt one already running under our labels, wait until it
answers, read its card, call it, stop it. The gateway's pool calls `DockerRunner` through asyncio.to_thread, so
the event loop stays free; Bench's perception service subclasses it (`labels_for`, `tag_for`, `start`).

`Encoder` talks to a running container over the Container API and knows nothing of Docker; `Container` owns one
container's lifecycle. This is the only module in the gateway that shells out.
"""
import fnmatch
import hashlib
import http.client
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .. import registry

DEMO_PREFIX = "medomni-demo"          # the name a container started outside the gateway gets
LABEL_NS = registry.LABEL_NS          # ownership labels, so adoption can be proven
BAKED_DATA = "/app/testdata"          # where an image keeps its own samples
READY_TIMEOUT = 180                   # ecgfounder reads 353 MiB of weights at start


class ContainerError(RuntimeError):
    """The container could not be started, or could not be reached."""


# ---------------- talking to a container ----------------

class Encoder:
    """One running container, over the Container API. Knows nothing of docker."""

    def __init__(self, url, timeout=120):
        self.url = url.rstrip("/")
        self.timeout = timeout          # per call; the gateway sets it from deployment.encode_timeout_s (m11)

    def _call(self, endpoint, body=None, timeout=None):
        timeout = timeout or self.timeout
        request = urllib.request.Request(self.url + endpoint)
        if body is not None:
            request.data = json.dumps(body).encode()
            request.add_header("content-type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            # A 400 is an answer, not a failure: the error model is part of the
            # API, so it is returned to the caller like any other response.
            try:
                return exc.code, json.load(exc)
            except ValueError:
                return exc.code, {"error": exc.reason}
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            # A container that is still starting can accept a connection and drop
            # it before answering, which arrives as RemoteDisconnected rather
            # than URLError. Both mean the same thing here: not up yet.
            reason = getattr(exc, "reason", None) or exc
            raise ContainerError(
                f"no container answered at {self.url} ({reason})") from None

    def healthz(self):
        return self._call("/healthz")[1]

    def card(self):
        return self._call("/card")[1]

    def encode(self, path, family=None, options=None):
        """Encode one path under /data. Returns the body, whatever the status.

        A caller error comes back as {"error": ...} rather than raising, because
        seeing the error model is half the point of this script.
        """
        body = {"family": family if family is not None else self.card()["family"],
                "path": path}
        if options:
            body["options"] = options
        return self._call("/encode", body)[1]

    def call(self, endpoint, body=None):
        """Status and body, for the deliberately bad requests below."""
        return self._call(endpoint, body)

    def ready(self, timeout=READY_TIMEOUT):
        """Wait for /healthz. False if it never answers."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.healthz()
                return True
            except ContainerError:
                time.sleep(0.5)
        return False


# ---------------- starting one ----------------

def _docker_or_explain():
    if not _which("docker"):
        raise ContainerError(
            "docker is not on PATH, so this script cannot start a container.\n"
            "Install a container runtime, or start the encoder yourself and pass --url.")
    if subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL) != 0:
        raise ContainerError(
            "docker is installed, but the daemon does not answer. Start it, then retry.")


def _which(name):
    from shutil import which
    return which(name)


def free_port(preferred=8080):
    """A port nothing is listening on, preferring the one asked for.

    Two encoders, or two runs of one encoder, then do not collide — and neither
    does a container someone left running on the usual port.
    """
    for candidate in (preferred, 0):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
                return probe.getsockname()[1]
            except OSError:
                continue
    raise ContainerError("no free port to publish the container on")


def port_available(port):
    """True when a valid host port is free on the loopback interface."""
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        return False
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _inspect(command):
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def labels_of(name):
    """The labels on a container, or None when there is no such container."""
    raw = _inspect(["docker", "inspect", "-f", "{{json .Config.Labels}}", name])
    if raw in (None, "", "null"):
        return None
    try:
        return json.loads(raw) or {}
    except ValueError:
        return None


def image_id_of(tag):
    """The image id a tag currently resolves to on this machine."""
    return _inspect(["docker", "image", "inspect", "-f", "{{.Id}}", tag])


class Container:
    """A started container, as a context manager.

        with Container("ecg-12lead-500hz-mv__ecgfounder") as encoder:
            print(encoder.card()["summary"])

    With `data`, that directory is mounted read-only at /data. With neither
    `data` nor an encoder directory to fall back on, the container reads the
    samples inside the image, which is how an image pulled from the registry is
    checked with no checkout and no data.
    """

    def __init__(self, encoder_id, data=None, baked=False, port=None,
                 build=False, keep=False, name=None, reuse=False,
                 ready_timeout=READY_TIMEOUT, labels=None, bind_host="127.0.0.1", tag=None, encoders_dir=None):
        self.encoder_id = encoder_id
        self.dir = Path(encoders_dir or registry.encoders_root()) / encoder_id.replace("__", "/", 1)
        if not baked and data is None and not self.dir.is_dir():
            raise ContainerError(f"no such encoder: {encoder_id}")
        self.tag = tag or registry.tag(encoder_id)   # the gateway passes its configured image_tag
        self.baked = baked
        self.data = None if baked else Path(data or self.dir / "testdata").resolve()
        self.port = port
        self.build = build
        self.keep = keep
        self.given_name = name          # a caller that owns the lifecycle names it
        self.reuse = reuse              # adopt that name when it is already running
        self.ready_timeout = ready_timeout
        self.labels = dict(labels or {})
        self.bind_host = bind_host      # loopback: an encoder is not a public service
        self.adopted = False
        self.name = None
        self.encoder = None

    # -- lifecycle --

    def __enter__(self):
        return self.start()

    def start(self):
        """Start the container and wait until it answers. Returns an Encoder.

        `__enter__` is exactly this, so a caller that owns the lifecycle itself —
        the gateway pool — starts an image the same way a demo does, and the
        promise that there is one implementation of it holds.
        """
        _docker_or_explain()
        if self.build:
            try:
                registry.build.build(self.dir)
            except registry.RegistryError as exc:
                raise ContainerError(str(exc)) from None
        if not self._image_present():
            raise ContainerError(
                f"no image {self.tag} on this machine.\n"
                f"Build it: medomni perception check {self.dir}   (or pull it: medomni perception pull)")

        if self.reuse and self.given_name:
            adopted = self._adopt()
            if adopted is not None:
                return adopted

        if self.port is None:
            self.port = free_port()
        elif not port_available(self.port):
            raise ContainerError(
                f"port {self.port} is not available. Select another port or omit --port.")
        # The port is part of the name, so two encoders, or one encoder twice,
        # never fight over it.
        self.name = self.given_name or f"{DEMO_PREFIX}-{self.encoder_id[:40]}-{self.port}"
        if self._container_present():
            # Adoption already declined it, so what is left is stopped or does not
            # answer. Remove it only when its labels prove it is ours: a container
            # that merely shares the name belongs to somebody else.
            if not (self.reuse and self._is_ours(labels_of(self.name))):
                raise ContainerError(
                    f"a container named {self.name} already exists and is not one of "
                    f"ours. Remove it with `docker rm -f {self.name}`, or select "
                    f"another name.")
            subprocess.call(["docker", "rm", "-f", self.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        run = ["docker", "run", "-d", "--name", self.name,
               "-p", f"{self.bind_host}:{self.port}:8080"]
        for key, value in sorted(self.labels.items()):
            run += ["--label", f"{key}={value}"]
        if self.baked:
            run += ["-e", f"DATA_ROOT={BAKED_DATA}"]
        else:
            if not self.data.is_dir():
                raise ContainerError(f"no such directory to mount: {self.data}")
            run += ["-v", f"{self.data}:/data:ro"]
        result = subprocess.run(run + [self.tag], capture_output=True, text=True)
        if result.returncode != 0:
            raise ContainerError(f"docker run failed: {result.stderr.strip()}")

        self.encoder = Encoder(f"http://127.0.0.1:{self.port}")
        if not self.encoder.ready(self.ready_timeout):
            logs = subprocess.run(["docker", "logs", "--tail", "20", self.name],
                                  capture_output=True, text=True)
            self.stop()
            raise ContainerError("the container never became ready. Its last output:\n"
                                 + (logs.stdout + logs.stderr).strip())
        return self.encoder

    def __exit__(self, *_):
        self.stop()
        return False

    def stop(self):
        if not self.name:
            return
        if self.keep:
            print(f"\nthe container is still running at {self.encoder.url}. Stop it with:"
                  f"\n    docker rm -f {self.name}")
        else:
            subprocess.call(["docker", "rm", "-f", self.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.name = None

    def _is_ours(self, labels):
        """True when every label we would set is already on that container.

        A name is not proof. Adopting on the name alone can attach to somebody
        else's container, on another image or another data root, and then report
        its answers under our card.
        """
        if not self.labels or not labels:
            return False
        return all(labels.get(key) == value for key, value in self.labels.items())

    def _adopt(self):
        """The container already running under `given_name`, if it is ours and answers.

        This is what makes "is it up already?" a real question rather than a
        collision: a container a previous run left behind is used instead of
        duplicated. Ownership is proven by label — see `_is_ours`.
        """
        running = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", self.given_name],
            capture_output=True, text=True)
        if running.returncode != 0 or running.stdout.strip() != "true":
            return None
        if not self._is_ours(labels_of(self.given_name)):
            return None
        # `docker port` answers one line per published address, IPv4 and IPv6.
        published = subprocess.run(["docker", "port", self.given_name, "8080/tcp"],
                                   capture_output=True, text=True)
        addresses = [line for line in published.stdout.split() if ":" in line]
        if published.returncode != 0 or not addresses:
            return None
        try:
            port = int(addresses[0].rsplit(":", 1)[1])
        except ValueError:
            return None

        encoder = Encoder(f"http://127.0.0.1:{port}")
        if not encoder.ready(self.ready_timeout):
            return None                 # start() removes it, once it is proven ours
        self.name, self.port, self.encoder, self.adopted = (
            self.given_name, port, encoder, True)
        return encoder

    def image_id(self):
        """The image this container actually runs, not the tag it was asked for."""
        if not self.name:
            return None
        return _inspect(["docker", "inspect", "-f", "{{.Image}}", self.name])

    # -- what it can read --

    def _image_present(self):
        result = subprocess.run(["docker", "image", "inspect", self.tag],
                                capture_output=True)
        return result.returncode == 0

    def _container_present(self):
        result = subprocess.run(["docker", "container", "inspect", self.name],
                                capture_output=True)
        return result.returncode == 0

    def samples(self):
        """Every `input*` sample the container can reach, in order.

        In baked mode the image is asked what it carries, so nothing here reads
        the repository. Otherwise the mounted directory is listed.
        """
        if self.baked:
            result = subprocess.run(["docker", "run", "--rm", self.tag,
                                     "ls", "-A", BAKED_DATA],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                raise ContainerError(
                    "could not list the samples in the image: " + result.stderr.strip())
            names = result.stdout.split()
        else:
            names = [p.name for p in self.data.iterdir() if p.is_file()]
        return sorted(n for n in names if fnmatch.fnmatch(n, "input*"))


# ---------------- the gateway's runner ----------------

MAX_NAME = 110
MANAGED_BY = "medomni-gateway"
IMAGE_ID_TTL = 5.0        # seconds a resolved tag is trusted, so a rebuild is noticed


class StartError(RuntimeError):
    """The container could not be started, or is not the encoder it should be."""


class Handle:
    """One live container."""

    def __init__(self, encoder_id, box, encoder, image_id):
        self.encoder_id = encoder_id
        self.box = box
        self.encoder = encoder
        self.name = box.name
        self.url = encoder.url
        self.adopted = box.adopted
        self.image_id = image_id

    def encode(self, body):
        return self.encoder.call("/encode", body)


class DockerRunner:
    def __init__(self, deployment):
        self.deployment = deployment
        self._image_ids = {}

    def name_for(self, encoder_id):
        """Name the container by every label that proves it is ours.

        labels_for lists those labels. A name that holds less identity than the
        labels lets two configurations want the same name. Adoption then refuses
        that container, and start() cannot remove it. This gives a 503 that never
        clears. The data root alone leaves out image_tag, and image_tag is also
        ownership. The digest comes first, so truncation at MAX_NAME keeps it.
        """
        identity = json.dumps(self.labels_for(encoder_id), sort_keys=True)
        digest = hashlib.sha256(identity.encode()).hexdigest()[:8]
        return f"{self.deployment.container_prefix}-{digest}-{encoder_id}"[:MAX_NAME]

    def tag_for(self, encoder_id):
        return registry.tag(encoder_id, self.deployment.image_tag)

    def labels_for(self, encoder_id):
        """What proves a container is ours, and ours for this configuration.

        Adoption compares these. Without them a container is claimed on its name
        alone, which can attach us to another image or another data root and let
        us report its answers under this card.
        """
        root = str(self.deployment.data_root or "")
        return {
            f"{LABEL_NS}.managed-by": MANAGED_BY,
            f"{LABEL_NS}.encoder-id": encoder_id,
            f"{LABEL_NS}.image": self.tag_for(encoder_id),
            f"{LABEL_NS}.data-root": hashlib.sha256(root.encode()).hexdigest()[:16],
        }

    def docker_available(self):
        try:
            _docker_or_explain()
            return True
        except ContainerError:
            return False

    def image_id(self, encoder_id):
        """The image id the tag resolves to now. Briefly memoized, so a rebuild shows."""
        tag = self.tag_for(encoder_id)
        cached = self._image_ids.get(tag)
        if cached and time.monotonic() - cached[1] < IMAGE_ID_TTL:
            return cached[0]
        found = image_id_of(tag)
        self._image_ids[tag] = (found, time.monotonic())
        return found

    def start(self, encoder_id):
        """Start the container, or adopt the one already running under our labels."""
        data_root = self.deployment.data_root
        box = Container(
            encoder_id,
            data=str(data_root) if data_root else None,
            baked=data_root is None,      # no data root: read the samples in the image
            name=self.name_for(encoder_id),
            reuse=True,
            ready_timeout=self.deployment.start_timeout_s,
            labels=self.labels_for(encoder_id),
            bind_host=self.deployment.bind_host,
            tag=self.tag_for(encoder_id),
        )
        try:
            encoder = box.start()
            encoder.timeout = self.deployment.encode_timeout_s
        except ContainerError as exc:
            raise StartError(str(exc)) from None

        # Adoption proved ownership by label; this proves the container is the
        # encoder we think it is. A card and an answer from different encoders
        # would compose Evidence that is internally inconsistent.
        try:
            card = encoder.card()
        except ContainerError as exc:
            box.stop()
            raise StartError(f"{encoder_id}: could not read its card ({exc})") from None
        if card.get("id") != encoder_id:
            box.stop()
            raise StartError(
                f"container for {encoder_id} reports id '{card.get('id')}'")

        self._image_ids.pop(self.tag_for(encoder_id), None)
        return Handle(encoder_id, box, encoder, box.image_id())

    def stop(self, handle):
        handle.box.stop()
