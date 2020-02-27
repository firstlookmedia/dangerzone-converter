FROM debian:buster

RUN apt-get update && \
    apt-get install -y sudo python3 python3-magic python3-pil poppler-utils imagemagick ghostscript tesseract-ocr tesseract-ocr-all libreoffice

# Fix imagemagick policy to allow writing PDFs
RUN sed -i '/rights="none" pattern="PDF"/c\<policy domain="coder" rights="read|write" pattern="PDF" />' /etc/ImageMagick-6/policy.xml

# Create an unprivileged user
RUN useradd -ms /bin/bash user

COPY scripts/* /usr/local/bin/
