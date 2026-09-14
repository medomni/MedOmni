FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 pillow==11.3.0 torch==2.6.0 torchvision==0.21.0 tqdm==4.67.1 ftfy==6.3.1 regex==2024.11.6
WORKDIR /app
COPY encoders/cxr-radiograph-2d/chexzero/assets.json encoders/cxr-radiograph-2d/chexzero/prepare_assets.py ./
COPY encoders/cxr-radiograph-2d/chexzero/assets ./assets
RUN python prepare_assets.py --verify-only
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/cxr-radiograph-2d/chexzero/adapter.py encoders/cxr-radiograph-2d/chexzero/card.yaml ./
COPY encoders/cxr-radiograph-2d/chexzero/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
