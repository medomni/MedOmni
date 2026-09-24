FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 pydicom==3.0.1
WORKDIR /app
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/retinal-heightmap-surfaces-f32/layer-thickness/adapter.py encoders/retinal-heightmap-surfaces-f32/layer-thickness/norms.py encoders/retinal-heightmap-surfaces-f32/layer-thickness/card.yaml ./
COPY encoders/retinal-heightmap-surfaces-f32/layer-thickness/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
