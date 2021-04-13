FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        ghostscript \
        graphicsmagick \
        libreoffice \
        poppler-utils \
        python3 \
        python3-magic \
        python3-pil \
        sudo \
        tesseract-ocr \
        tesseract-ocr-all \
        && \
    apt-get upgrade --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --no-log-init --create-home --shell /bin/bash user

COPY scripts/* /usr/local/bin/
