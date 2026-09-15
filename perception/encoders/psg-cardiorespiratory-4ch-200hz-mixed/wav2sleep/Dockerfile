FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.7.1
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.3.1 scipy==1.16.1 edfio==0.4.16 hydra-core==1.3.2 omegaconf==2.3.0 pandas==2.3.2 pyarrow==21.0.0 pyedflib==0.1.42 huggingface-hub==0.34.4 numba==0.62.1 "setuptools<81"
WORKDIR /app
COPY encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/assets.json encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/prepare_assets.py ./
COPY encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/assets ./assets
RUN python prepare_assets.py --verify-only && pip install --no-deps ./assets/source
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/adapter.py encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/card.yaml ./
COPY encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
