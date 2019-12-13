from debian:buster

WORKDIR /tmp
RUN apt-get update
RUN apt-get install -y software-properties-common wget gnupg
RUN add-apt-repository 'deb http://mirror.wazo.community/debian pelican-buster main'
RUN wget http://mirror.wazo.community/wazo_current.key
RUN apt-key add wazo_current.key
RUN apt-get update
RUN apt-get -y install asterisk asterisk-dev librabbitmq-dev make gcc libcurl4-openssl-dev git jq wazo-res-stasis-amqp wazo-res-amqp asterisk-sounds-main strace net-tools lsof procps vim

# clean up previous conf
RUN rm -rf /etc/asterisk/*

# Install Asterisk consul module
WORKDIR /usr/src
run git clone https://github.com/sboily/asterisk-consul-module
WORKDIR /usr/src/asterisk-consul-module
RUN CFLAGS=-g make
RUN make install
RUN make samples

# Patch AMQP stasis module
WORKDIR /usr/src
run git clone https://github.com/wazo-platform/wazo-res-stasis-amqp
WORKDIR /usr/src/wazo-res-stasis-amqp
RUN cp amqp.json /usr/share/asterisk/rest-api
RUN bin/patch_ari_resources.sh

ADD etc/asterisk/* /etc/asterisk/

ENTRYPOINT /usr/sbin/asterisk -f
