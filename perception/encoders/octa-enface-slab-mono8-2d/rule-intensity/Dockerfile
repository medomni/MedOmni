FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 pydicom==3.0.1 pillow==11.3.0 pylibjpeg==2.1.0 pylibjpeg-libjpeg==2.3.0 pylibjpeg-openjpeg==2.6.0
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/octa-enface-slab-mono8-2d/rule-intensity/adapter.py encoders/octa-enface-slab-mono8-2d/rule-intensity/card.yaml ./
COPY encoders/octa-enface-slab-mono8-2d/rule-intensity/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
