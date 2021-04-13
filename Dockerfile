FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive && \
    export DEBIAN_FRONTEND && \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
        ghostscript \
        graphicsmagick \
        libreoffice \
        poppler-utils \
        python3 \
        python3-magic \
        python3-pil \
        tesseract-ocr \
        tesseract-ocr-all \
        && \
    apt-get upgrade --yes && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --no-log-init --create-home --shell /bin/bash -K UID_MIN=10000 -K GID_MIN=10000 user

COPY scripts/* /usr/local/bin/

# /tmp is where the first convert expects the input file to be, and
# where it will write the pixel files
#
# /dangerzone is where the second script expects files to be put by the first one
#
# /safezone is where the wrapper eventually moves the sanitized files.
VOLUME /dangerzone /tmp /safezone

USER user

# to run this:
#
# PIXEL_DIR=pixels
# SAFE_DIR=safe
# DOCKER_HARDENING="--network none --security-opt=no-new-privileges:true"
# mkdir $PIXEL_DIR $SAFE_DIR
# chmod g+w $PIXEL_DIR $SAFE_DIR
# sudo chown 10000 $PIXEL_DIR $SAFE_DIR
# docker run $DOCKER_HARDENING -v $PIXEL_DIR:/dangerzone -v $DOCUMENT_FILENAME:/tmp/input_file flmcode/dangerzone document-to-pixels-unpriv
# docker run $DOCKER_HARDENING -v $PIXEL_DIR:/dangerzone -v $SAFE_DIR:/safezone -e OCR=$OCR -e OCR_LANGUAGE=$OCR_LANG flmcode/dangerzone pixels-to-pdf-unpriv
