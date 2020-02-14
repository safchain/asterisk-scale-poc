#!/bin/bash

docker run --net=host --rm -v ${PWD}:/wazo-applicationd-client openapitools/openapi-generator-cli generate -i http://localhost:8000/openapi.json -g python --package-name wazo_applicationd_client -o /wazo-applicationd-client

sudo chown -R $UID:$UID $PWD
