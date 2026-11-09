# Build from the repository root, so the runtime and Core are in context:
#   docker build -f perception/encoders/fundus-faf-mono8-2d/retinograd/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# The assets come first, because this layer is the expensive one: it downloads
# 623 MiB of weights. Changing a pin below then costs a pip install and not
# another download. fetch_assets.py verifies every file against the sha256 the
# card publishes, so a build cannot ship an image whose card describes other
# weights. It is a file rather than a RUN heredoc because the classic builder
# accepts a heredoc, ignores its body, and reports success.
ENV RETINOGRAD_SOURCE=/opt/retinograd \
    RETINOGRAD_WEIGHTS=/opt/weights/FAF_inception_resenet_2Class_classification.pth
COPY perception/encoders/fundus-faf-mono8-2d/retinograd/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights /opt/retinograd

# CPU wheels: much smaller than the CUDA ones, and deployment.yaml decides the
# device, not the image. torchvision is not installed — the adapter resizes
# with Pillow, which is what torchvision's Resize does to a PIL image anyway.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0

# timm supplies the inception_resnet_v2 architecture; the checkpoint supplies
# every weight in it, so nothing is ever downloaded at run time.
# pydicom and pillow are the family decoder's, not this model's: FAF arrives as
# a JPEG-compressed DICOM, and pillow is what pydicom decodes it with.
RUN pip install --no-cache-dir \
        timm==1.0.11 \
        pydicom==3.0.1 \
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
COPY perception/encoders/fundus-faf-mono8-2d/retinograd/adapter.py ./
COPY perception/encoders/fundus-faf-mono8-2d/retinograd/card.yaml ./
COPY perception/encoders/fundus-faf-mono8-2d/retinograd/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
