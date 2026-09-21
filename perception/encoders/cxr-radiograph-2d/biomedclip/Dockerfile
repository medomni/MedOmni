FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 pillow==11.3.0 torch==2.6.0 torchvision==0.21.0 open_clip_torch==2.32.0 transformers==4.49.0
WORKDIR /app
COPY encoders/cxr-radiograph-2d/biomedclip/assets.json encoders/cxr-radiograph-2d/biomedclip/prepare_assets.py ./
COPY encoders/cxr-radiograph-2d/biomedclip/assets ./assets
RUN python prepare_assets.py --verify-only
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/cxr-radiograph-2d/biomedclip/adapter.py encoders/cxr-radiograph-2d/biomedclip/card.yaml ./
COPY encoders/cxr-radiograph-2d/biomedclip/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
