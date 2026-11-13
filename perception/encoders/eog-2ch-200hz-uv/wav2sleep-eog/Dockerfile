FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.7.1
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.3.1 scipy==1.16.1 edfio==0.4.16 hydra-core==1.3.2 omegaconf==2.3.0 pandas==2.3.2 pyarrow==21.0.0 pyedflib==0.1.42 huggingface-hub==0.34.4 numba==0.62.1 "setuptools<81"
WORKDIR /app
COPY src/medomni/perception/runtime/assets.py perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/assets.json ./
COPY perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/assets ./assets
RUN python assets.py --verify-only && pip install --no-deps ./assets/source

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/adapter.py perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/card.yaml ./
COPY perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
