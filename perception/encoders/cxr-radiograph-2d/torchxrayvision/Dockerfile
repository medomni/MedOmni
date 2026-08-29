# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/cxr-radiograph-2d__torchxrayvision/Dockerfile -t <tag> .
FROM python:3.11-slim

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
    && sha256sum /opt/weights/*

WORKDIR /app
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/cxr-radiograph-2d__torchxrayvision/adapter.py ./
COPY encoders/cxr-radiograph-2d__torchxrayvision/card.yaml ./
# Test data travels with the image, so the smoke test needs no dataset access.
COPY encoders/cxr-radiograph-2d__torchxrayvision/testdata ./testdata

ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
