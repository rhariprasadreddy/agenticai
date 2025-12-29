# Gaudi + PyTorch 2.7.1 base (SynapseAI 1.22.1)
FROM vault.habana.ai/gaudi-docker/1.22.1/ubuntu22.04/habanalabs/pytorch-installer-2.7.1:latest

# Runtime envs
ENV PT_HPU_LAZY_MODE=0 \
    HF_HOME=/root/.cache/huggingface \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# Pin a compatible matrix (matches what just worked)
COPY docker/constraints.txt /tmp/constraints.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /tmp/constraints.txt

# Optional: create a default local Gaudi config dir
RUN mkdir -p /workspace/gaudi2_cfg
COPY docker/gaudi_config.json /workspace/gaudi2_cfg/gaudi_config.json

# Workdir and entrypoint
WORKDIR /workspace
# We keep code and data bind-mounted; entrypoint only opens a shell unless CMD is provided
ENTRYPOINT ["/bin/bash", "-lc"]

