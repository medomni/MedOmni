FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 edfio==0.4.16 pobm==1.2.0 numpy==1.26.4 scipy==1.15.3
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/spo2-series-10hz-pct/pobm/adapter.py encoders/spo2-series-10hz-pct/pobm/card.yaml ./
COPY encoders/spo2-series-10hz-pct/pobm/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
