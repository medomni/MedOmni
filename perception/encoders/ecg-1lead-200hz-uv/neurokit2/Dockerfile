FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 edfio==0.4.16 neurokit2==0.2.13 numpy==2.2.6 scipy==1.15.3 pandas==2.2.3
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/ecg-1lead-200hz-uv/neurokit2/adapter.py encoders/ecg-1lead-200hz-uv/neurokit2/card.yaml ./
COPY encoders/ecg-1lead-200hz-uv/neurokit2/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
