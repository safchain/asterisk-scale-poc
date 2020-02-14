#!/bin/bash

echo ---------------------------------------------------------
echo
echo Note: requires 
echo     - https://github.com/LucyBot-Inc/api-spec-converter
echo
echo ---------------------------------------------------------

PORT=${PORT:-56566}

if [ -z "$ASTERISK_SRC" ]; then
	echo "Please set the ASTERISK_SRC environment variable"
	exit -1
fi

cp -R $ASTERISK_SRC/rest-api /tmp/rest-api
ln -s /tmp/rest-api /tmp/rest-api/ari
sed -i -e "s/localhost:8088/localhost:$PORT/" /tmp/rest-api/resources.json

python -m http.server -d /tmp/rest-api $PORT &
HTTP_PID=$!

api-spec-converter --from=swagger_1 --to=swagger_2 --syntax=json --order=alpha http://localhost:$PORT/resources.json > /tmp/swagger2.json

kill $HTTP_PID

cat /tmp/swagger2.json | jq '.definitions |= . + {"containers": {"description": "random dict", "type": "object", "properties": {"additionalProperties": {}}}}' > /tmp/fixes.json
cat /tmp/fixes.json | jq '.definitions |= . + {"binary": {"description": "random string", "type": "string"}}' > /tmp/swagger2.json

api-spec-converter --from=swagger_2 --to=openapi_3 --syntax=json --order=alpha /tmp/swagger2.json > /tmp/openapi3.json

cat /tmp/openapi3.json | jq '. |= . + {"security": [{"basicAuth": []}]}' | jq '.components |= . + {"securitySchemes": {"basicAuth": {"type": "http", "scheme": "basic"}}}' | jq '.components.parameters |= . + {"asteriskID": {"in": "header", "name": "X-Asterisk-ID", "required": false, "schema": {"type": "string"}}}' | jq '.paths[][].parameters |= . + [{"$ref": "#/components/parameters/asteriskID"}]' | jq '.paths[][] |= del(.operationId)' > /tmp/fixes.json

api-spec-converter --from=openapi_3 --to=openapi_3 --syntax=yaml --order=alpha /tmp/fixes.json > openapi3.yaml

docker run --rm -v ${PWD}:/wazo-appgateway-client openapitools/openapi-generator-cli generate -i /wazo-appgateway-client/openapi3.yaml -g python --library asyncio --package-name wazo_appgateway_client -o /wazo-appgateway-client

sudo chown -R $UID:$UID $PWD

# patches
patch wazo_appgateway_client/api_client.py <<EOF
243a244,254
>     def deserialize_obj(self, data, response_type):
>         """Deserializes data into an object.
> 
>         :param data: data to be deserialized.
>         :param response_type: class literal for
>             deserialized object, or string of class name.
> 
>         :return: deserialized object.
>         """
>         return self.__deserialize(data, response_type)
> 
EOF

rm -rf /tmp/rest-api
