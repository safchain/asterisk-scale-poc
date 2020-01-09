from python:3.7-buster

RUN apt-get update
RUN apt-get -y install sox libsox-fmt-mp3

ADD app_sdk/ /apps/app_sdk
ADD conf/ /apps/conf

WORKDIR /apps/conf
RUN pip install -r requirements.txt

CMD python /apps/conf/conf.py
