# Build from the repository root, so the runtime and Core are in context:
#   docker build -f perception/encoders/octa-flowcube-mono8-3d/flow-metrics/Dockerfile -t <tag> .
#
# No model, no weights, no network: the measures are computed from the cube.
# scikit-image supplies Otsu's threshold and the skeletonisation, because the
# measures are the literature's and so should their implementation be.
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir \
        scikit-image==0.25.2 \
        pydicom==3.0.1 \
        pylibjpeg==2.0.1 \
        pylibjpeg-libjpeg==2.3.0 pylibjpeg-openjpeg==2.6.0 \
        pillow==11.0.0 \
        numpy==2.2.6 \
        pyyaml==6.0.2
WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/octa-flowcube-mono8-3d/flow-metrics/adapter.py ./
COPY perception/encoders/octa-flowcube-mono8-3d/flow-metrics/card.yaml ./
COPY perception/encoders/octa-flowcube-mono8-3d/flow-metrics/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
