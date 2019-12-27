# How to generate

## Python

```
docker run --rm -v ${PWD}:/local swaggerapi/swagger-codegen-cli generate -i /local/ari.json  -l python --library asyncio -o /local/out/python
```
