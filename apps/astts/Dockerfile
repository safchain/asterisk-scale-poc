from python:3.7-buster

RUN apt-get update
RUN apt-get -y install sox libsox-fmt-mp3

ADD app_sdk/ /apps/app_sdk
ADD astts/ /apps/astts

WORKDIR /apps/astts
RUN pip install -r requirements.txt

CMD python /apps/astts/astts.py
