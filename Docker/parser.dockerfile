FROM python:3.8-alpine
ADD requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt
WORKDIR /source
ENV PYTHONIOENCODING=utf-8
CMD python3 /source/CianParserMain.py
