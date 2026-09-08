# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/cxr-radiograph-2d/torchxrayvision/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# CPU wheels. They are much smaller than the CUDA wheels, and deployment.yaml
# decides the device (README phase 7), not the image.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0

RUN pip install --no-cache-dir \
        torchxrayvision==1.5.4 \
        scikit-image==0.26.0 \
        numpy==2.4.6 \
        pillow==12.3.0 \
        pyyaml==6.0.2

# The weights travel inside the image, in a world-readable directory. The
# container then reads no network at run time, and needs no writable home.
ENV XRV_WEIGHTS_DIR=/opt/weights
RUN python -c "import torchxrayvision as xrv; \
        xrv.models.DenseNet(weights='densenet121-res224-all', cache_dir='/opt/weights')" \
    && chmod -R a+rX /opt/weights \
    && echo "56524913dd16a906422e8d8b66a7a5c46be1d82eb7ac012d8103776f1aa68899  /opt/weights/nih-pc-chex-mimic_ch-google-openi-kaggle-densenet121-d121-tw-lr001-rot45-tr15-sc15-seed0-best.pt" \
       | sha256sum -c -

WORKDIR /app
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/cxr-radiograph-2d/torchxrayvision/adapter.py ./
COPY encoders/cxr-radiograph-2d/torchxrayvision/card.yaml ./
# Test data travels with the image, so the smoke test needs no dataset access.
COPY encoders/cxr-radiograph-2d/torchxrayvision/testdata ./testdata

ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
