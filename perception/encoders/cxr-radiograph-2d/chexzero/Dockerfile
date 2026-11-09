FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 pillow==11.3.0 torch==2.6.0 torchvision==0.21.0 tqdm==4.67.1 ftfy==6.3.1 regex==2024.11.6
WORKDIR /app
COPY src/medomni/perception/runtime/assets.py perception/encoders/cxr-radiograph-2d/chexzero/assets.json ./
COPY perception/encoders/cxr-radiograph-2d/chexzero/assets ./assets
RUN python assets.py --verify-only

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/cxr-radiograph-2d/chexzero/adapter.py perception/encoders/cxr-radiograph-2d/chexzero/card.yaml ./
COPY perception/encoders/cxr-radiograph-2d/chexzero/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
