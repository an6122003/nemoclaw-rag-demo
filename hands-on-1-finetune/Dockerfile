# Hands-on 1 training image.
#
# NVIDIA's NGC PyTorch container (the one the DGX Spark fine-tuning playbooks
# use; its PyTorch is built for the Spark's GB10 GPU) plus:
#   * transformers + peft + accelerate for LoRA training
#   * llama.cpp's GGUF converter (Python only, nothing is compiled)
#
# setup.sh builds it once, so the lab itself needs no internet access:
#   docker build -t workshop-finetune:latest hands-on-1-finetune/

ARG BASE_IMAGE=nvcr.io/nvidia/pytorch:25.11-py3
FROM ${BASE_IMAGE}

# llama.cpp switched to semantic version tags; v0.4.1 was current when this lab
# was written.
ARG LLAMA_CPP_REF=v0.4.1

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# Pin the image's own torch so no dependency can swap it for a generic wheel
# that does not know the GB10 GPU.
RUN python -c "import torch; print('torch==' + torch.__version__)" > /opt/torch-pin.txt \
 && pip install -c /opt/torch-pin.txt \
        "transformers>=4.51,<5" "peft>=0.15,<1" "accelerate>=1.6,<2" \
        sentencepiece protobuf safetensors \
 && python -c "import torch, transformers, peft; print('torch', torch.__version__, '| transformers', transformers.__version__, '| peft', peft.__version__)"

# Only the converter and its two local packages are kept from the checkout.
RUN git clone --depth 1 --branch "${LLAMA_CPP_REF}" https://github.com/ggml-org/llama.cpp /tmp/llama.cpp \
 && mkdir -p /opt/llama.cpp \
 && cp -r /tmp/llama.cpp/convert_hf_to_gguf.py /tmp/llama.cpp/conversion /tmp/llama.cpp/gguf-py /opt/llama.cpp/ \
 && rm -rf /tmp/llama.cpp \
 && pip install -c /opt/torch-pin.txt /opt/llama.cpp/gguf-py \
 && python /opt/llama.cpp/convert_hf_to_gguf.py --help > /dev/null

ENV LLAMA_CPP_CONVERT=/opt/llama.cpp/convert_hf_to_gguf.py
WORKDIR /workspace
