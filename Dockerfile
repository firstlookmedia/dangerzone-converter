FROM ubuntu:20.04

ENV LANG="en_US.UTF-8":"ko_KR.UTF-8"
ENV LANGUAGE = "ko_KR:ko:en_GB:en"

RUN apt-get update && \
    apt-get install -y --no-install-recommends sudo python3 python3-magic python3-pil poppler-utils graphicsmagick ghostscript tesseract-ocr libreoffice tesseract-ocr-all && \
    apt-get install -y --no-install-recommends python3-pip xvfb xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic wkhtmltopdf flashplugin-nonfree language-pack-ko && \
    pip3 install --pre pyhwp six && \
    locale-gen ko_KR.UTF-8 && \
    apt-get install -y --no-install-recommends fonts-nanum fonts-nanum-coding fonts-nanum-extra fcitx-hangul && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash user

COPY ./script/* /usr/local/bin/
