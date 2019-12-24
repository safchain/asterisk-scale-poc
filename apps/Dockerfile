from python:3.7-buster

RUN apt-get update
RUN apt-get -y install sox libsox-fmt-mp3

ADD app.py /apps/
ADD astts.py /apps/
ADD requirements.txt /apps/

RUN pip install -r /apps/requirements.txt

CMD python /apps/astts.py
