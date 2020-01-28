FROM wazopbx/wazo-auth

RUN apt-get update
RUN apt-get install -y jq

ADD ./entry.sh /entry.sh

ENTRYPOINT /entry.sh