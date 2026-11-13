# Build from the repository root, so the runtime and Core are in context:
#   docker build -f perception/encoders/oct-volume-raster-mono8-3d/mirage/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

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
        pylibjpeg-libjpeg==2.3.0 pylibjpeg-openjpeg==2.6.0 \
        pillow==11.0.0 \
        numpy==2.2.6 \
        pyyaml==6.0.2

# The weights come after the packages (R-171), so the package layers can be shared with other images.
# This layer downloads 332 MiB of weights; fetch_assets.py verifies every file against the sha256 the card publishes, so a build
# cannot ship an image whose card describes other weights.
ENV MIRAGE_SOURCE=/opt/mirage \
    MIRAGE_WEIGHTS=/opt/weights/model.safetensors
COPY perception/encoders/oct-volume-raster-mono8-3d/mirage/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights /opt/mirage

WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/oct-volume-raster-mono8-3d/mirage/adapter.py ./
COPY perception/encoders/oct-volume-raster-mono8-3d/mirage/card.yaml ./
COPY perception/encoders/oct-volume-raster-mono8-3d/mirage/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
