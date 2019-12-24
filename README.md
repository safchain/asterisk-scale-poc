# Asterisk Scale

## How to start

```
docker-compose up -V
```

This will start :

* Asterisk
* Kamailio
* Consul
* Nginx (aka api-gateway)
* Rabbitmq
* The demo App

## How to test

SIP :

* username: demo
* password: demo

Once registered you can call the number `8001`, you should hear which asterisk you are connected to. This is the demo App which answers to the call and play the sound.

## How to scale

```
docker-compose scale asterisk=3
```

Calling the number `8001` multiple times you should hear different Asterisk IDs.