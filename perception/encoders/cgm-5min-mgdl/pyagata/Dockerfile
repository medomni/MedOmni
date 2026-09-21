# Build context: perception/
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 py-agata==0.0.8 numpy==2.2.6 pandas==2.2.3 scipy==1.15.3
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/cgm-5min-mgdl/pyagata/adapter.py encoders/cgm-5min-mgdl/pyagata/card.yaml ./
COPY encoders/cgm-5min-mgdl/pyagata/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
