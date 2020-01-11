FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y python3 python3-magic python3-pil poppler-utils imagemagick ghostscript tesseract-ocr tesseract-ocr-all libreoffice

# Fix imagemagick policy to allow writing PDFs
RUN sed -i '/rights="none" pattern="PDF"/c\<policy domain="coder" rights="read|write" pattern="PDF" />' /etc/ImageMagick-6/policy.xml

COPY scripts/document-to-pixels /usr/local/bin/document-to-pixels
COPY scripts/pixels-to-pdf /usr/local/bin/pixels-to-pdf
