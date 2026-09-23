# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/oct-volume-raster-mono8-3d/mirage/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# Assets first: this layer downloads 332 MiB of weights, so changing a pin
# below costs a pip install and not another download. fetch_assets.py verifies
# every file against the sha256 the card publishes.
ENV MIRAGE_SOURCE=/opt/mirage \
    MIRAGE_WEIGHTS=/opt/weights/model.safetensors
COPY encoders/oct-volume-raster-mono8-3d/mirage/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights /opt/mirage

# CPU wheels: much smaller than the CUDA ones, and deployment.yaml decides the
# device, not the image.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0

# mirage_hf.py imports einops and requests at module scope; safetensors reads
# the checkpoint. pydicom and pillow are the family decoder's, not this model's:
# an OCT volume arrives as a multi-frame JPEG-lossless DICOM, and pylibjpeg is
# what pydicom decompresses that transfer syntax with.
RUN pip install --no-cache-dir \
        einops==0.8.1 \
        requests==2.32.3 \
        safetensors==0.4.5 \
        pydicom==3.0.1 \
        pylibjpeg==2.0.1 \
        pylibjpeg-libjpeg==2.3.0 \
        pillow==11.0.0 \
        numpy==2.2.6 \
        pyyaml==6.0.2

WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/oct-volume-raster-mono8-3d/mirage/adapter.py ./
COPY encoders/oct-volume-raster-mono8-3d/mirage/card.yaml ./
# Test data travels with the image, so the smoke test needs no dataset access.
COPY encoders/oct-volume-raster-mono8-3d/mirage/testdata ./testdata

ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
