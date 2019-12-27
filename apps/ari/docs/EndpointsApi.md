# swagger_client.EndpointsApi

All URIs are relative to *http://localhost:8088/ari*

Method | HTTP request | Description
------------- | ------------- | -------------
[**endpoints_get**](EndpointsApi.md#endpoints_get) | **GET** /endpoints | List all endpoints.
[**endpoints_send_message_put**](EndpointsApi.md#endpoints_send_message_put) | **PUT** /endpoints/sendMessage | Send a message to some technology URI or endpoint.
[**endpoints_tech_get**](EndpointsApi.md#endpoints_tech_get) | **GET** /endpoints/{tech} | List available endoints for a given endpoint technology.
[**endpoints_tech_resource_get**](EndpointsApi.md#endpoints_tech_resource_get) | **GET** /endpoints/{tech}/{resource} | Details for an endpoint.
[**endpoints_tech_resource_send_message_put**](EndpointsApi.md#endpoints_tech_resource_send_message_put) | **PUT** /endpoints/{tech}/{resource}/sendMessage | Send a message to some endpoint in a technology.


# **endpoints_get**
> list[Endpoint] endpoints_get(x_asterisk_id=x_asterisk_id)

List all endpoints.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure HTTP basic authorization: basicAuth
configuration = swagger_client.Configuration()
configuration.username = 'YOUR_USERNAME'
configuration.password = 'YOUR_PASSWORD'

# create an instance of the API class
api_instance = swagger_client.EndpointsApi(swagger_client.ApiClient(configuration))
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # List all endpoints.
    api_response = api_instance.endpoints_get(x_asterisk_id=x_asterisk_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling EndpointsApi->endpoints_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

[**list[Endpoint]**](Endpoint.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **endpoints_send_message_put**
> endpoints_send_message_put(to, _from, x_asterisk_id=x_asterisk_id, body=body, variables=variables)

Send a message to some technology URI or endpoint.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure HTTP basic authorization: basicAuth
configuration = swagger_client.Configuration()
configuration.username = 'YOUR_USERNAME'
configuration.password = 'YOUR_PASSWORD'

# create an instance of the API class
api_instance = swagger_client.EndpointsApi(swagger_client.ApiClient(configuration))
to = 'to_example' # str | The endpoint resource or technology specific URI to send the message to. Valid resources are sip, pjsip, and xmpp.
_from = '_from_example' # str | The endpoint resource or technology specific identity to send this message from. Valid resources are sip, pjsip, and xmpp.
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)
body = 'body_example' # str | The body of the message (optional)
variables = [swagger_client.ConfigTuple()] # list[ConfigTuple] |  (optional)

try:
    # Send a message to some technology URI or endpoint.
    api_instance.endpoints_send_message_put(to, _from, x_asterisk_id=x_asterisk_id, body=body, variables=variables)
except ApiException as e:
    print("Exception when calling EndpointsApi->endpoints_send_message_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **to** | **str**| The endpoint resource or technology specific URI to send the message to. Valid resources are sip, pjsip, and xmpp. | 
 **_from** | **str**| The endpoint resource or technology specific identity to send this message from. Valid resources are sip, pjsip, and xmpp. | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 
 **body** | **str**| The body of the message | [optional] 
 **variables** | [**list[ConfigTuple]**](ConfigTuple.md)|  | [optional] 

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **endpoints_tech_get**
> list[Endpoint] endpoints_tech_get(tech, x_asterisk_id=x_asterisk_id)

List available endoints for a given endpoint technology.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure HTTP basic authorization: basicAuth
configuration = swagger_client.Configuration()
configuration.username = 'YOUR_USERNAME'
configuration.password = 'YOUR_PASSWORD'

# create an instance of the API class
api_instance = swagger_client.EndpointsApi(swagger_client.ApiClient(configuration))
tech = 'tech_example' # str | Technology of the endpoints (sip,iax2,...)
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # List available endoints for a given endpoint technology.
    api_response = api_instance.endpoints_tech_get(tech, x_asterisk_id=x_asterisk_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling EndpointsApi->endpoints_tech_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tech** | **str**| Technology of the endpoints (sip,iax2,...) | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

[**list[Endpoint]**](Endpoint.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **endpoints_tech_resource_get**
> Endpoint endpoints_tech_resource_get(tech, resource, x_asterisk_id=x_asterisk_id)

Details for an endpoint.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure HTTP basic authorization: basicAuth
configuration = swagger_client.Configuration()
configuration.username = 'YOUR_USERNAME'
configuration.password = 'YOUR_PASSWORD'

# create an instance of the API class
api_instance = swagger_client.EndpointsApi(swagger_client.ApiClient(configuration))
tech = 'tech_example' # str | Technology of the endpoint
resource = 'resource_example' # str | ID of the endpoint
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # Details for an endpoint.
    api_response = api_instance.endpoints_tech_resource_get(tech, resource, x_asterisk_id=x_asterisk_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling EndpointsApi->endpoints_tech_resource_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tech** | **str**| Technology of the endpoint | 
 **resource** | **str**| ID of the endpoint | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

[**Endpoint**](Endpoint.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **endpoints_tech_resource_send_message_put**
> endpoints_tech_resource_send_message_put(tech, resource, _from, x_asterisk_id=x_asterisk_id, body=body, variables=variables)

Send a message to some endpoint in a technology.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# Configure HTTP basic authorization: basicAuth
configuration = swagger_client.Configuration()
configuration.username = 'YOUR_USERNAME'
configuration.password = 'YOUR_PASSWORD'

# create an instance of the API class
api_instance = swagger_client.EndpointsApi(swagger_client.ApiClient(configuration))
tech = 'tech_example' # str | Technology of the endpoint
resource = 'resource_example' # str | ID of the endpoint
_from = '_from_example' # str | The endpoint resource or technology specific identity to send this message from. Valid resources are sip, pjsip, and xmpp.
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)
body = 'body_example' # str | The body of the message (optional)
variables = [swagger_client.ConfigTuple()] # list[ConfigTuple] |  (optional)

try:
    # Send a message to some endpoint in a technology.
    api_instance.endpoints_tech_resource_send_message_put(tech, resource, _from, x_asterisk_id=x_asterisk_id, body=body, variables=variables)
except ApiException as e:
    print("Exception when calling EndpointsApi->endpoints_tech_resource_send_message_put: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **tech** | **str**| Technology of the endpoint | 
 **resource** | **str**| ID of the endpoint | 
 **_from** | **str**| The endpoint resource or technology specific identity to send this message from. Valid resources are sip, pjsip, and xmpp. | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 
 **body** | **str**| The body of the message | [optional] 
 **variables** | [**list[ConfigTuple]**](ConfigTuple.md)|  | [optional] 

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

