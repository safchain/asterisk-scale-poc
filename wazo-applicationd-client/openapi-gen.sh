#!/bin/bash

docker run --rm -v ${PWD}:/wazo-applicationd-client openapitools/openapi-generator-cli generate -i http://192.168.1.230:8000/openapi.json -g python --package-name wazo-applicationd-client -o /wazo-applicationd-client

sudo chown -R $UID:$UID $PWD
