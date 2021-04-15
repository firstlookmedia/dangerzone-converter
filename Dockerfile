FROM debian:buster-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends sudo python3 python3-magic python3-pil poppler-utils graphicsmagick ghostscript tesseract-ocr tesseract-ocr-all libreoffice && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash user

COPY scripts/* /usr/local/bin/
