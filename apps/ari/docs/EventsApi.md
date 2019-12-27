# swagger_client.EventsApi

All URIs are relative to *http://localhost:8088/ari*

Method | HTTP request | Description
------------- | ------------- | -------------
[**events_get**](EventsApi.md#events_get) | **GET** /events | WebSocket connection for events.
[**events_user_event_name_post**](EventsApi.md#events_user_event_name_post) | **POST** /events/user/{eventName} | Generate a user event.


# **events_get**
> Message events_get(app, x_asterisk_id=x_asterisk_id, subscribe_all=subscribe_all)

WebSocket connection for events.

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
api_instance = swagger_client.EventsApi(swagger_client.ApiClient(configuration))
app = ['app_example'] # list[str] | Applications to subscribe to.
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)
subscribe_all = true # bool | Subscribe to all Asterisk events. If provided, the applications listed will be subscribed to all events, effectively disabling the application specific subscriptions. Default is 'false'. (optional)

try:
    # WebSocket connection for events.
    api_response = api_instance.events_get(app, x_asterisk_id=x_asterisk_id, subscribe_all=subscribe_all)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling EventsApi->events_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **app** | [**list[str]**](str.md)| Applications to subscribe to. | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 
 **subscribe_all** | **bool**| Subscribe to all Asterisk events. If provided, the applications listed will be subscribed to all events, effectively disabling the application specific subscriptions. Default is &#39;false&#39;. | [optional] 

### Return type

[**Message**](Message.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **events_user_event_name_post**
> events_user_event_name_post(event_name, application, x_asterisk_id=x_asterisk_id, source=source, variables=variables)

Generate a user event.

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
api_instance = swagger_client.EventsApi(swagger_client.ApiClient(configuration))
event_name = 'event_name_example' # str | Event name
application = 'application_example' # str | The name of the application that will receive this event
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)
source = ['source_example'] # list[str] | URI for event source (channel:{channelId}, bridge:{bridgeId}, endpoint:{tech}/{resource}, deviceState:{deviceName} (optional)
variables = [swagger_client.ConfigTuple()] # list[ConfigTuple] | The \"variables\" key in the body object holds custom key/value pairs to add to the user event. Ex. { \"variables\": { \"key\": \"value\" } } (optional)

try:
    # Generate a user event.
    api_instance.events_user_event_name_post(event_name, application, x_asterisk_id=x_asterisk_id, source=source, variables=variables)
except ApiException as e:
    print("Exception when calling EventsApi->events_user_event_name_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **event_name** | **str**| Event name | 
 **application** | **str**| The name of the application that will receive this event | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 
 **source** | [**list[str]**](str.md)| URI for event source (channel:{channelId}, bridge:{bridgeId}, endpoint:{tech}/{resource}, deviceState:{deviceName} | [optional] 
 **variables** | [**list[ConfigTuple]**](ConfigTuple.md)| The \&quot;variables\&quot; key in the body object holds custom key/value pairs to add to the user event. Ex. { \&quot;variables\&quot;: { \&quot;key\&quot;: \&quot;value\&quot; } } | [optional] 

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

