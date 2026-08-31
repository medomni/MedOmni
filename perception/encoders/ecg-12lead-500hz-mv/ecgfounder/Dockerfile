# Build from the perception/ directory, so the shared runtime is in context:
#   docker build -f encoders/ecg-12lead-500hz-mv__ecgfounder/Dockerfile -t <tag> .
FROM python:3.11-slim@sha256:1042b61448fef4ba92d16a8c7eb4996d027568ce64792a7877fd88511e0af7c6

# The assets come first, and the dependencies after, because this layer is the
# expensive one: it downloads 353 MiB of weights. Changing a pin below then
# costs a pip install and not another download.
#
# fetch_assets.py verifies every download against the sha256 the card publishes,
# so a build cannot ship an image whose card describes other weights. It is a
# file and not a `RUN <<EOF` heredoc because the classic builder accepts a
# heredoc, ignores its body, and reports success — the assets silently would not
# arrive. It needs only the standard library, which is why it can run first.
ENV ECGFOUNDER_SOURCE=/opt/ecgfounder \
    ECGFOUNDER_LABELS=/opt/ecgfounder/tasks.txt \
    ECGFOUNDER_WEIGHTS=/opt/weights/12_lead_ECGFounder.pth \
    PYTHONPATH=/opt/ecgfounder
COPY encoders/ecg-12lead-500hz-mv__ecgfounder/fetch_assets.py /tmp/
RUN python3 /tmp/fetch_assets.py \
    && rm /tmp/fetch_assets.py \
    && chmod -R a+rX /opt/weights /opt/ecgfounder

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

WORKDIR /app
COPY runtime/serve.py runtime/contract.py ./
COPY encoders/ecg-12lead-500hz-mv__ecgfounder/adapter.py ./
COPY encoders/ecg-12lead-500hz-mv__ecgfounder/card.yaml ./
# Test data travels with the image, so the smoke test needs no dataset access.
COPY encoders/ecg-12lead-500hz-mv__ecgfounder/testdata ./testdata

ENV APP_DIR=/app DATA_ROOT=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "/app/serve.py", "serve"]
