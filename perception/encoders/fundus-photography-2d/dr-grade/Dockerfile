# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/fundus-photography-2d/dr-grade/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# Assets first: fetch_assets.py verifies both files against the sha256 the card
# publishes, so a build cannot ship an image whose card describes other weights.
ENV DR_GRADE_WEIGHTS=/opt/weights/model.safetensors
COPY encoders/fundus-photography-2d/dr-grade/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights

# CPU wheels: much smaller than the CUDA ones, and deployment.yaml decides the
# device, not the image.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0

# timm supplies the efficientnet_b0 architecture and the checkpoint supplies
# every weight in it. No torchvision: the adapter resizes and crops with
# Pillow, which is what torchvision does to a PIL image anyway. pydicom and
# pillow are the family decoder's — a fundus photograph arrives as a DICOM.
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
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/fundus-photography-2d/dr-grade/adapter.py ./
COPY encoders/fundus-photography-2d/dr-grade/card.yaml ./
COPY encoders/fundus-photography-2d/dr-grade/testdata ./testdata

ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
