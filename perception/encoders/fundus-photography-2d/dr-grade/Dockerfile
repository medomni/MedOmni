# Build from the repository root, so the runtime and Core are in context:
#   docker build -f perception/encoders/fundus-photography-2d/dr-grade/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# Assets first: fetch_assets.py verifies both files against the sha256 the card
# publishes, so a build cannot ship an image whose card describes other weights.
ENV DR_GRADE_WEIGHTS=/opt/weights/model.safetensors
COPY perception/encoders/fundus-photography-2d/dr-grade/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights

# CPU wheels: much smaller than the CUDA ones, and deployment.yaml decides the
# device, not the image. torch 2.15.0 and torchvision 0.29.2 are what this image
# has run since timm first pulled them in from PyPI (R-171): installing them here,
# from the CPU index, keeps that version and leaves timm nothing to fetch.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.15.0 torchvision==0.29.2

# timm supplies the efficientnet_b0 architecture and the checkpoint supplies
# every weight in it. The adapter resizes and crops with Pillow, not
# torchvision. pydicom and pillow are the family decoder's — a fundus
# photograph arrives as a DICOM.
RUN pip install --no-cache-dir \
        timm==1.0.11 \
        safetensors==0.4.5 \
        pydicom==3.0.1 \
        pylibjpeg==2.0.1 \
        pylibjpeg-openjpeg==2.4.0 \
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
COPY perception/encoders/fundus-photography-2d/dr-grade/adapter.py ./
COPY perception/encoders/fundus-photography-2d/dr-grade/card.yaml ./
COPY perception/encoders/fundus-photography-2d/dr-grade/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
