# Build context: perception/
# pylibjpeg decodes the JPEG-lossless multi-frame volumes this family arrives in.
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0
RUN pip install --no-cache-dir pyyaml==6.0.2 pydicom==3.0.1 pillow==11.3.0 numpy==2.2.6 timm==1.0.29 \
        pylibjpeg==2.0.1 pylibjpeg-libjpeg==2.3.0 pylibjpeg-openjpeg==2.6.0
WORKDIR /app
COPY encoders/oct-volume-raster-mono8-3d/kdoct/assets/model.pth /opt/weights/model.pth
ENV KDOCT_WEIGHTS=/opt/weights/model.pth
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/oct-volume-raster-mono8-3d/kdoct/adapter.py encoders/oct-volume-raster-mono8-3d/kdoct/card.yaml ./
COPY encoders/oct-volume-raster-mono8-3d/kdoct/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
