FROM python:3.12-slim
# Agent infrastructure, not analysis tools (D-2 toolset unchanged): terminus-2 runs `tmux -V` and
# installs tmux/asciinema at setup if missing — impossible on the closed atomnet, so every agent failed
# to start (harness live check, 2026-09-24). Installed here, at BUILD time, where the network is open.
RUN apt-get update && apt-get install -y --no-install-recommends tmux asciinema \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pandas==2.2.3 scikit-learn==1.5.2 requests==2.32.3 httpx==0.27.2 \
    wfdb==4.1.2 pyedflib==0.1.38 pydicom==2.4.4 h5py==3.11.0 pillow==10.4.0
# R3 (bundle-1): the modality readers agents otherwise reinstall per run (wfdb/edf/dicom/h5/images)
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
RUN mkdir -p /workspace/submission /workspace/data
# nothing task-specific baked in; bootstrap stages data (see docker-compose.yaml)
