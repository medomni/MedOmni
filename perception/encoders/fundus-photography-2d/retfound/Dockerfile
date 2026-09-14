# Build context: perception/
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6 AS dependencies
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0
RUN pip install --no-cache-dir pyyaml==6.0.2 pydicom==3.0.1 pillow==11.3.0 numpy==2.2.6 timm==1.0.29
FROM dependencies
WORKDIR /app
COPY encoders/fundus-photography-2d/retfound/assets /opt/retfound
COPY encoders/fundus-photography-2d/retfound/prepare_assets.py encoders/fundus-photography-2d/retfound/card.yaml ./
RUN python prepare_assets.py --verify-only --directory /opt/retfound
ENV PYTHONPATH=/opt/retfound
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/fundus-photography-2d/retfound/adapter.py encoders/fundus-photography-2d/retfound/card.yaml ./
COPY encoders/fundus-photography-2d/retfound/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
