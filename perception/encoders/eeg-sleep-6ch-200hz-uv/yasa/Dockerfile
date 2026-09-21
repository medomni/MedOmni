# Build context: perception/
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pyyaml==6.0.2 edfio==0.4.16 yasa==0.7.0 numpy==2.2.6 pandas==2.2.3 scipy==1.15.3 mne==1.10.2 lightgbm==4.6.0 scikit-learn==1.6.1
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/eeg-sleep-6ch-200hz-uv/yasa/adapter.py encoders/eeg-sleep-6ch-200hz-uv/yasa/card.yaml ./
COPY encoders/eeg-sleep-6ch-200hz-uv/yasa/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
