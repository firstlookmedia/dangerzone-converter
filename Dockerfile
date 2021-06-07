FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive && \
    export DEBIAN_FRONTEND && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
    default-jre \
    ghostscript \
    graphicsmagick \
    libreoffice \
    libreoffice-java-common \
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

# /tmp/input_file is where the first convert expects the input file to be, and
# /tmp where it will write the pixel files
#
# /dangerzone is where the second script expects files to be put by the first one
#
# /safezone is where the wrapper eventually moves the sanitized files.
VOLUME /dangerzone /tmp/input_file /safezone
