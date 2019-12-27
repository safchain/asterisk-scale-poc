# swagger_client.PlaybacksApi

All URIs are relative to *http://localhost:8088/ari*

Method | HTTP request | Description
------------- | ------------- | -------------
[**playbacks_playback_id_control_post**](PlaybacksApi.md#playbacks_playback_id_control_post) | **POST** /playbacks/{playbackId}/control | Control a playback.
[**playbacks_playback_id_delete**](PlaybacksApi.md#playbacks_playback_id_delete) | **DELETE** /playbacks/{playbackId} | Stop a playback.
[**playbacks_playback_id_get**](PlaybacksApi.md#playbacks_playback_id_get) | **GET** /playbacks/{playbackId} | Get a playback&#39;s details.


# **playbacks_playback_id_control_post**
> playbacks_playback_id_control_post(playback_id, operation, x_asterisk_id=x_asterisk_id)

Control a playback.

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
api_instance = swagger_client.PlaybacksApi(swagger_client.ApiClient(configuration))
playback_id = 'playback_id_example' # str | Playback's id
operation = 'operation_example' # str | Operation to perform on the playback.
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # Control a playback.
    api_instance.playbacks_playback_id_control_post(playback_id, operation, x_asterisk_id=x_asterisk_id)
except ApiException as e:
    print("Exception when calling PlaybacksApi->playbacks_playback_id_control_post: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **playback_id** | **str**| Playback&#39;s id | 
 **operation** | **str**| Operation to perform on the playback. | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **playbacks_playback_id_delete**
> playbacks_playback_id_delete(playback_id, x_asterisk_id=x_asterisk_id)

Stop a playback.

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
api_instance = swagger_client.PlaybacksApi(swagger_client.ApiClient(configuration))
playback_id = 'playback_id_example' # str | Playback's id
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # Stop a playback.
    api_instance.playbacks_playback_id_delete(playback_id, x_asterisk_id=x_asterisk_id)
except ApiException as e:
    print("Exception when calling PlaybacksApi->playbacks_playback_id_delete: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **playback_id** | **str**| Playback&#39;s id | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

void (empty response body)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **playbacks_playback_id_get**
> Playback playbacks_playback_id_get(playback_id, x_asterisk_id=x_asterisk_id)

Get a playback's details.

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
api_instance = swagger_client.PlaybacksApi(swagger_client.ApiClient(configuration))
playback_id = 'playback_id_example' # str | Playback's id
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # Get a playback's details.
    api_response = api_instance.playbacks_playback_id_get(playback_id, x_asterisk_id=x_asterisk_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling PlaybacksApi->playbacks_playback_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **playback_id** | **str**| Playback&#39;s id | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

[**Playback**](Playback.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

