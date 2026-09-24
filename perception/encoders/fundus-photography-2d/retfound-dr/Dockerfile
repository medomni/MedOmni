# Build context: perception/
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6 AS dependencies
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0
RUN pip install --no-cache-dir pyyaml==6.0.2 pydicom==3.0.1 pillow==11.3.0 numpy==2.2.6 timm==1.0.29

# The published checkpoint also holds optimizer state (3.6 GB); only the model reaches the image.
FROM dependencies AS weights
COPY encoders/fundus-photography-2d/retfound-dr/assets/checkpoint.pth /tmp/checkpoint.pth
COPY encoders/fundus-photography-2d/retfound-dr/strip_checkpoint.py /tmp/
RUN python /tmp/strip_checkpoint.py /tmp/checkpoint.pth /tmp/model.pth

FROM dependencies
WORKDIR /app
COPY --from=weights /tmp/model.pth /opt/weights/model.pth
COPY encoders/fundus-photography-2d/retfound-dr/assets/models_vit.py encoders/fundus-photography-2d/retfound-dr/assets/LICENSE /opt/retfound/
ENV PYTHONPATH=/opt/retfound RETFOUND_DR_WEIGHTS=/opt/weights/model.pth
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/fundus-photography-2d/retfound-dr/adapter.py encoders/fundus-photography-2d/retfound-dr/card.yaml ./
COPY encoders/fundus-photography-2d/retfound-dr/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
