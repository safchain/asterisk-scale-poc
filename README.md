# Asterisk Scale Experimentations

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
* The Text-to-Speech demo app
* The Conference demo app
* wazo-auth
* wazo-websocketd

## How to test

SIP registration :

* username: demo
* password: demo

### Text-to-Speech

Once registered you can call the number `8001`, you should hear which asterisk you are connected to. This is the demo App which answers to the call and play the sound.

Calling the number `8001` multiple times you should hear different Asterisk IDs.

### Conference

Once registered you can call the number `7001`, you will be placed in a conference room whatever Asterisk you will be connected to.

## How to scale

```
docker-compose scale asterisk=2
```

## How to start wazo-applicationd

```
cd wazo-applicationd
pip install -r requirements.txt
wazo-applicationd --debug
````

By default it will listen 8000. API documentation is available at
http://localhost:8000/docs


## Generate client library

### appgateway-client

Use by applicationd thus as to be generated before using applicationd. 

```
cd wazo-applicationd-client
./openapi-gen.sh
```

### applicationd-client

```
cd wazo-applicationd-client
./openapi-gen.sh
```
## Applicationd demo app

* apps/wazo-app-test


## Architecture

```
                     +----------+
                     |          |
      +--------------+ asterisk +---------------+
      |              |          |               |
      |              +----+-----+               |
      |                   |                     |
      |                   |                     |
      |                   |                     |
      |                   |                     |
+-----+------+         +--+----+           +----+---+
|            |         |       |           |        |
|  rabbitmq  |         | nginx |           | consul |
|            |         |       |           |        |
+-----+----+-+         +---+---+           +---+----+
      |    |               |                   |
      |    |               |                   |
      |    +----------+    |    +--------------+
      |               |    |    |
      |               |    |    |
+-----+------+      +-+----+----+--+
|            |      |              |
| websocketd |      | applicationd |
|            |      |              |
+-----+------+      +-------+------+
      |                     |
      |                     |
      |                     |
      |                     |
      |                     |
      |      +-------+      |
      |      |       |      |
      +------+  app  +------+
             |       |
             +-------+
```

## Resources

* https://github.com/safchain/asyncio-ari-ast-id
  Asyncio ARI library supporting extra parameter in order to handle communication with the API Gateway

* https://gitub.com/lebauce/consul-c
  C library to talk with Consul API

* https://github.com/lebauce/asterisk-res-consul/tree/scale
  Asterisk module with primitives to handle connections to Consul

* https://github.com/lebauce/asterisk-res-consul-discovery/tree/scale
  Asterisk module to register Asterisk instances into Consul

* https://github.com/lebauce/asterisk-res-consul-stasis-app/tree/scale
  Asterisk module to create Stasis applications from applications registered in Consul

* https://github.com/wazo-platform/wazo-res-amqp/tree/scale
  Asterisk module for AMQP bus communication

* https://github.com/wazo-platform/wazo-res-stasis-amqp/tree/scale
  Asterisk module forwarding Stasis message through AMQP bus