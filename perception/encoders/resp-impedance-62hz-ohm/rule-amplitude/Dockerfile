FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 wfdb==4.3.0 pandas==2.2.3
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/resp-impedance-62hz-ohm/rule-amplitude/adapter.py encoders/resp-impedance-62hz-ohm/rule-amplitude/card.yaml ./
COPY encoders/resp-impedance-62hz-ohm/rule-amplitude/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
