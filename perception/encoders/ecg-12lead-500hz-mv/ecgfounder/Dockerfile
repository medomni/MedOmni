# Build from the repository root, so the runtime and Core are in context:
#   docker build -f perception/encoders/ecg-12lead-500hz-mv/ecgfounder/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# CPU wheels. They are much smaller than the CUDA wheels, and deployment.yaml
# decides the device (README phase 7), not the image. No torchvision: net1d.py
# does not import it, unlike torchxrayvision's transforms.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0

# wfdb reads the record, at the version upstream pins. It brings scipy, pandas
# and matplotlib with it, and net1d.py imports matplotlib too, so nothing here
# is installed for only one of the two.
#
# pandas is pinned, and pinned low. Left to resolve, pip takes pandas 3, where a
# string column's .values is a StringArray and wfdb 4.2.0 raises TypeError while
# importing. This is the collision the README's one-container-per-encoder rule
# is about, so the whole tree is pinned rather than only the direct dependency.
RUN pip install --no-cache-dir \
        wfdb==4.2.0 \
        pandas==2.2.3 \
        numpy==2.4.6 \
        pyyaml==6.0.2

# The weights come after the packages (R-171), so the package layers can be shared with other images.
# This layer downloads 353 MiB of weights; fetch_assets.py verifies every file against the sha256 the card publishes, so a build
# cannot ship an image whose card describes other weights.
# It is a file and not a `RUN <<EOF` heredoc because the classic builder accepts a heredoc, ignores its body, and reports success.
ENV ECGFOUNDER_SOURCE=/opt/ecgfounder \
    ECGFOUNDER_LABELS=/opt/ecgfounder/tasks.txt \
    ECGFOUNDER_WEIGHTS=/opt/weights/12_lead_ECGFounder.pth \
    PYTHONPATH=/opt/ecgfounder
COPY perception/encoders/ecg-12lead-500hz-mv/ecgfounder/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights /opt/ecgfounder

WORKDIR /app

# The runtime (R-117) and the Core modules it uses (families, contracts, R-120), under /app/medomni.
RUN pip install --no-cache-dir pydantic==2.14.2
COPY src/medomni/__init__.py medomni/
COPY src/medomni/core medomni/core
COPY src/medomni/perception/__init__.py medomni/perception/
COPY src/medomni/perception/runtime medomni/perception/runtime
COPY core/families core/families
# The encoder: its adapter, card and test data (test data travels with the image).
COPY perception/encoders/ecg-12lead-500hz-mv/ecgfounder/adapter.py ./
COPY perception/encoders/ecg-12lead-500hz-mv/ecgfounder/card.yaml ./
COPY perception/encoders/ecg-12lead-500hz-mv/ecgfounder/testdata ./testdata
ENV PYTHONPATH=/app:/opt/ecgfounder MEDOMNI_ROOT=/app APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "medomni.perception.runtime.serve", "serve"]
