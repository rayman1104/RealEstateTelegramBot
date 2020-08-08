FROM python:3.8-alpine
RUN apk add --update --no-cache --virtual .build-deps \
        g++ \
        python3-dev \
        libxml2 \
        libxml2-dev && \
    apk add libxslt-dev && \
    pip3 install lxml && \
    apk del .build-deps
ADD requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt
WORKDIR /source
ENV PYTHONIOENCODING=utf-8
CMD python3 BotTelegram.py
