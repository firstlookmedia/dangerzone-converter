FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends sudo python3 python3-magic python3-pil poppler-utils graphicsmagick ghostscript tesseract-ocr tesseract-ocr-all libreoffice && \
    apt-get install -y --no-install-recommends python3-pip xvfb xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic wkhtmltopdf flashplugin-nonfree language-pack-ko && \
    apt-get install -y --no-install-recommends fonts-nanum fonts-nanum-coding fonts-nanum-extra fcitx-hangul && \    
    pip3 install --pre pyhwp six && \
    locale-gen ko_KR.UTF-8 && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash user

ENV LANG="en_US.UTF-8":"ko_KR.UTF-8"
ENV LANGUAGE = "ko_KR:ko:en_GB:en"

COPY scripts/* /usr/local/bin/
