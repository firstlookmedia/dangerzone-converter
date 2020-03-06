FROM debian:buster

RUN apt-get update && \
    apt-get install -y sudo python3 python3-magic python3-pil poppler-utils graphicsmagick ghostscript tesseract-ocr tesseract-ocr-all libreoffice

RUN useradd -ms /bin/bash user

COPY scripts/* /usr/local/bin/
