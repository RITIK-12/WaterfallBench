# Sandbox image for WaterfallBench-Pilot tasks: the agent's environment, not the service.
#
# Hosted Valkyrie creates sandboxes from a registry image (ImageSource), so build this for
# linux/amd64, push it to a registry your sandbox provider can pull from, and set
# WFB_SANDBOX_IMAGE on the service to that reference:
#
#   docker build --platform linux/amd64 -t REGISTRY/waterfallbench-sandbox:v1 sandbox-image
#   docker push REGISTRY/waterfallbench-sandbox:v1
#
# The image holds no task data: setup_task uploads each task's documents at run time.
FROM --platform=linux/amd64 python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# poppler-utils: pdftotext / pdfinfo / pdftoppm. The rest are what CLI agents commonly expect.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      poppler-utils ca-certificates curl git jq less file procps bash \
 && rm -rf /var/lib/apt/lists/*

RUN pip install \
      "pypdf==5.1.0" \
      "pdfplumber==0.11.4" \
      "pandas==2.2.3" \
      "numpy==2.1.3" \
      "lxml==5.3.0" \
      "beautifulsoup4==4.12.3"

RUN mkdir -p /workspace/docs /workspace/reports
WORKDIR /workspace
