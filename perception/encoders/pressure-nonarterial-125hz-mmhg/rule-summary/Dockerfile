FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 wfdb==4.3.0 pandas==2.2.3
WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/pressure-nonarterial-125hz-mmhg/rule-summary/adapter.py perception/encoders/pressure-nonarterial-125hz-mmhg/rule-summary/card.yaml ./
COPY perception/encoders/pressure-nonarterial-125hz-mmhg/rule-summary/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
