# medomni-perception: the perception service an encoder-arm atom runs beside its agent (R-147). Build from the
# repository root:
#   docker build -f src/medomni/perception/sidecar/Dockerfile -t medomni-perception .
# The image holds a minimal repository at /app (WORKDIR): pyproject.toml marks it, so the gateway finds Core's family
# files and the encoder cards at their repository paths.
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
# docker CLI only (the daemon is the host's, via the mounted socket)
ADD https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz /tmp/docker.tgz
RUN tar -xzf /tmp/docker.tgz -C /tmp && mv /tmp/docker/docker /usr/local/bin/ && rm -rf /tmp/docker* \
    && pip install --no-cache-dir fastapi==0.162.0 "uvicorn[standard]==0.54.0" pydantic==2.14.2 pyyaml==6.0.3 \
       requests==2.34.2 inotify_simple==2.0.1
WORKDIR /app
COPY pyproject.toml ./
# Core and Perception only: the gateway, the runtime's input manifests, the registry's card check, this service
COPY src/medomni/__init__.py src/medomni/
COPY src/medomni/core src/medomni/core
COPY src/medomni/perception src/medomni/perception
# the catalogue checks encoder cards against Core's family files
COPY core/families core/families
# encoder cards (and the adapter.py and Dockerfile that make one runnable), the deployment record and defaults
COPY perception/encoders perception/encoders
COPY perception/deployed.yaml perception/deployment.yaml perception/
ENV PYTHONPATH=/app/src MEDOMNI_ROOT=/app PYTHONUNBUFFERED=1 DATA_ROOT=/workspace/data PORT=8899
EXPOSE 8899
HEALTHCHECK --interval=5s --timeout=3s --start-period=180s --retries=30 \
    CMD python3 -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8899/healthz', timeout=2)"
CMD ["python3", "-m", "medomni.perception.sidecar"]
