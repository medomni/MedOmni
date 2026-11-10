"""The perception service (R-147): the gateway, run as one container beside an atom's agent.

Perception owns the service. Bench finds it through the `medomni.services` entry point `perception`, checks its image
before an encoder-arm run, and talks to it only over the Gateway API at `PERCEPTION_URL` (http://perception:8899).
Atoms' compose files (Studio's renderer) run the image under the service name `perception`.

    SERVICE.image                 the image tag atoms' compose files run
    SERVICE.build_command(repo)   the `docker build` argv for that image, from the repository root (not run here)
    SERVICE.present()             whether the image is on this machine

The service itself is in service.py (`python -m medomni.perception.sidecar`); importing this package imports no
gateway code.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DOCKERFILE = "src/medomni/perception/sidecar/Dockerfile"  # under the repository root, which is the build context


@dataclass(frozen=True)
class ServiceImage:
    name: str      # the compose service name, and the host name the agent dials
    image: str     # the image tag
    port: int
    dockerfile: Path

    @property
    def url(self) -> str:
        return f"http://{self.name}:{self.port}"

    def build_command(self, repo) -> list[str]:
        """The argv that builds the image, with the repository root as the build context."""
        repo = Path(repo)
        return ["docker", "build", "-f", str(repo / DOCKERFILE), "-t", self.image, str(repo)]

    def present(self) -> bool:
        """True when the image is on this machine (`docker image inspect`). False without Docker."""
        try:
            return subprocess.run(["docker", "image", "inspect", self.image], capture_output=True).returncode == 0
        except OSError:
            return False


SERVICE = ServiceImage(name="perception", image="medomni-perception", port=8899,
                       dockerfile=Path(__file__).resolve().parent / "Dockerfile")
