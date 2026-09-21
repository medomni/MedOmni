FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.6.0
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 scipy==1.15.3 edfio==0.4.16 wfdb==4.2.0 pandas==2.2.3 matplotlib==3.10.1
WORKDIR /app
COPY encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/assets.json encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/prepare_assets.py ./
COPY encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/assets ./assets
RUN python prepare_assets.py --verify-only
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/adapter.py encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/card.yaml ./
COPY encoders/ecg-monitor-3to5lead-250hz-continuous/ecgfounder/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
