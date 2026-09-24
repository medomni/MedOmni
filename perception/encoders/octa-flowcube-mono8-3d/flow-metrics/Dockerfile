# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/octa-flowcube-mono8-3d/flow-metrics/Dockerfile -t <tag> .
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
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/octa-flowcube-mono8-3d/flow-metrics/adapter.py ./
COPY encoders/octa-flowcube-mono8-3d/flow-metrics/card.yaml ./
COPY encoders/octa-flowcube-mono8-3d/flow-metrics/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
