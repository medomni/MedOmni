FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6
# pylibjpeg decodes the JPEG 2000 and JPEG-lossless slabs this family arrives in.
RUN pip install --no-cache-dir pyyaml==6.0.2 numpy==2.2.6 scipy==1.15.3 pydicom==3.0.1 \
        pylibjpeg==2.0.1 pylibjpeg-libjpeg==2.3.0 pylibjpeg-openjpeg==2.6.0
WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/octa-enface-slab-mono8-2d/vessel-density/adapter.py perception/encoders/octa-enface-slab-mono8-2d/vessel-density/norms.py perception/encoders/octa-enface-slab-mono8-2d/vessel-density/card.yaml ./
COPY perception/encoders/octa-enface-slab-mono8-2d/vessel-density/testdata ./testdata
ENV PYTHONPATH=/app MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
