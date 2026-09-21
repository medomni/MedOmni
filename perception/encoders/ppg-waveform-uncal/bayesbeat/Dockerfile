FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 scipy==1.15.3 torch==2.6.0 torchviz==0.0.3 scikit-learn==1.6.1 edfio==0.4.16 wfdb==4.2.0 pandas==2.2.3
WORKDIR /app
COPY encoders/ppg-waveform-uncal/bayesbeat/assets.json encoders/ppg-waveform-uncal/bayesbeat/prepare_assets.py ./
COPY encoders/ppg-waveform-uncal/bayesbeat/assets ./assets
RUN python prepare_assets.py --verify-only
COPY runtime/serve.py runtime/contract.py runtime/family_alias.generated.yaml ./
COPY encoders/ppg-waveform-uncal/bayesbeat/adapter.py encoders/ppg-waveform-uncal/bayesbeat/card.yaml ./
COPY encoders/ppg-waveform-uncal/bayesbeat/testdata ./testdata
ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
