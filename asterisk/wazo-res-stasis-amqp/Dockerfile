FROM debian:buster
MAINTAINER Wazo Maintainers <dev@wazo.community>

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -q update && apt-get -q -y install \
    apt-utils \
    gnupg \
    wget
RUN echo "deb http://mirror.wazo.community/debian/ wazo-dev-buster main" > /etc/apt/sources.list.d/wazo-dist.list
RUN wget http://mirror.wazo.community/wazo_current.key -O - | apt-key add -
RUN apt-get -q update && apt-get -q -y install \
    wazo-libsccp \
    git \
    make \
    gcc \
    g++ \
    asterisk \
    libedit-dev \
    wazo-res-amqp

RUN  apt-get install --assume-yes openssl libxml2-dev libncurses5-dev uuid-dev sqlite3 libsqlite3-dev pkg-config libjansson-dev

RUN apt-get install --assume-yes asterisk-dev wazo-res-amqp-dev librabbitmq-dev

COPY . /usr/src/wazo-res-stasis-amqp
RUN cd /usr/src/wazo-res-stasis-amqp && \
    make && \
    make install DOCDIR=/usr/share/asterisk

EXPOSE 2000 5038 5039 5060/udp

CMD ["asterisk", "-dvf"]
