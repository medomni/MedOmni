"""What `medomni perception new <family>/<encoder>` writes: an encoder folder to fill in, with an empty testdata/.

The adapter follows the runtime's adapter interface (FAMILY, load, encode); the card skeleton names every field
Core's model card contract needs, with TODO where a person must decide; the Dockerfile uses the image layout every
encoder shares. `medomni studio testdata <encoder>` fills testdata/, and `medomni perception check --freeze`
writes its expected.json.
"""
from pathlib import Path

ADAPTER = '''"""{family} encoder: {name}. Write load() and encode(); the runtime does the rest."""
from medomni.perception.runtime import Degraded, labels

FAMILY = "{family}"


def load():
    """Load the model once, at start. Its result reaches encode as options["_model"]."""
    return None


def encode(sample, options):
    """A decoded {family} sample in, a list of output blocks out. Raise Degraded for input you cannot use."""
    raise Degraded("TODO: encode is not written yet")
'''

CARD = '''id: {family}__{name}
family: {family}
modality: TODO
summary: TODO one line on what the encoder reports
authors:
- name: TODO
intended_use: TODO
limits: []
outputs:
- kind: labels
  scale: probability
  labels: []
options: {{}}
reliability:
  status: unmeasured
non_training: true
license: TODO
source:
  url: TODO
  rev: TODO
acceptance: pending
'''

DOCKERFILE = '''# Build context: the repository root (docker build -f perception/encoders/{family}/{name}/Dockerfile .)
FROM python:3.11-slim
# TODO: the model's own dependencies, each pinned (pip install name==version).
WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pyyaml==6.0.2 pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/{family}/{name}/adapter.py perception/encoders/{family}/{name}/card.yaml ./
COPY perception/encoders/{family}/{name}/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
'''

DOCKERIGNORE = '''# Only what the Dockerfile beside this file copies (BuildKit reads <Dockerfile>.dockerignore).
*
!core/families
!perception/encoders/{family}/{name}/adapter.py
!perception/encoders/{family}/{name}/card.yaml
!perception/encoders/{family}/{name}/testdata
!src/medomni/__init__.py
!src/medomni/core
!src/medomni/perception/__init__.py
!src/medomni/perception/runtime
**/__pycache__
**/*.pyc
'''


def write(target, family, name):
    target = Path(target)
    (target / "testdata").mkdir(parents=True)
    files = {"adapter.py": ADAPTER, "card.yaml": CARD, "Dockerfile": DOCKERFILE,
             "Dockerfile.dockerignore": DOCKERIGNORE}
    out = []
    for fname, text in files.items():
        p = target / fname
        p.write_text(text.format(family=family, name=name), encoding="utf-8")
        out.append(p)
    (target / "testdata" / ".gitkeep").write_text("")
    return out + [target / "testdata"]
