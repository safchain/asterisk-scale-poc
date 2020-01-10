from debian:buster

WORKDIR /tmp
RUN apt-get update
RUN apt-get install -y software-properties-common wget gnupg
RUN add-apt-repository 'deb http://mirror.wazo.community/debian pelican-buster main'
RUN wget http://mirror.wazo.community/wazo_current.key
RUN apt-key add wazo_current.key
RUN apt-get update
RUN apt-get -y install asterisk asterisk-dev librabbitmq-dev make gcc libcurl4-openssl-dev \
    git jq asterisk-sounds-main strace net-tools lsof \
    procps vim libjansson-dev curl

# clean up previous conf
RUN rm -rf /etc/asterisk/*

# Install Asterisk consul module
RUN git clone --single-branch --branch scale https://github.com/lebauce/asterisk-res-consul /usr/src/asterisk-res-consul
WORKDIR /usr/src/asterisk-res-consul
RUN CFLAGS=-g make
RUN make clean
RUN make install
#RUN make samples

# Install Asterisk consul discovery module
RUN git clone --single-branch --branch scale https://github.com/lebauce/asterisk-res-consul-discovery /usr/src/asterisk-res-consul-discovery
WORKDIR /usr/src/asterisk-res-consul-discovery
RUN CFLAGS=-g make
RUN make clean
RUN make install
#RUN make samples

# Install Asterisk consul app module
RUN git clone --single-branch --branch scale https://github.com/lebauce/asterisk-res-consul-stasis-app /usr/src/asterisk-res-consul-stasis-app
WORKDIR /usr/src/asterisk-res-consul-stasis-app
RUN make clean
RUN CFLAGS=-g make
RUN make install
#RUN make samples

RUN git clone --single-branch --branch scale https://github.com/wazo-platform/wazo-res-amqp.git /usr/src/wazo-res-amqp
WORKDIR /usr/src/wazo-res-amqp
RUN make clean
RUN CFLAGS=-g make
RUN make install

RUN git clone --single-branch --branch scale https://github.com/wazo-platform/wazo-res-stasis-amqp.git /usr/src/wazo-res-stasis-amqp
WORKDIR /usr/src/wazo-res-stasis-amqp
RUN make clean
RUN CFLAGS="-I../wazo-res-amqp -g" make
RUN make install

ADD etc/asterisk/* /etc/asterisk/

ENTRYPOINT /usr/sbin/asterisk -f

#ADD ./entry.sh /
#ENTRYPOINT /entry.sh