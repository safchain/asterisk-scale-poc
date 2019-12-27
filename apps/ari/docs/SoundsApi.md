# swagger_client.SoundsApi

All URIs are relative to *http://localhost:8088/ari*

Method | HTTP request | Description
------------- | ------------- | -------------
[**sounds_get**](SoundsApi.md#sounds_get) | **GET** /sounds | List all sounds.
[**sounds_sound_id_get**](SoundsApi.md#sounds_sound_id_get) | **GET** /sounds/{soundId} | Get a sound&#39;s details.


# **sounds_get**
> list[Sound] sounds_get(x_asterisk_id=x_asterisk_id, lang=lang, format=format)

List all sounds.

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
api_instance = swagger_client.SoundsApi(swagger_client.ApiClient(configuration))
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)
lang = 'lang_example' # str | Lookup sound for a specific language. (optional)
format = 'format_example' # str | Lookup sound in a specific format. (optional)

try:
    # List all sounds.
    api_response = api_instance.sounds_get(x_asterisk_id=x_asterisk_id, lang=lang, format=format)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SoundsApi->sounds_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 
 **lang** | **str**| Lookup sound for a specific language. | [optional] 
 **format** | **str**| Lookup sound in a specific format. | [optional] 

### Return type

[**list[Sound]**](Sound.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **sounds_sound_id_get**
> Sound sounds_sound_id_get(sound_id, x_asterisk_id=x_asterisk_id)

Get a sound's details.

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
api_instance = swagger_client.SoundsApi(swagger_client.ApiClient(configuration))
sound_id = 'sound_id_example' # str | Sound's id
x_asterisk_id = 'x_asterisk_id_example' # str | Asterisk ID used to route the request through the API Gateway (optional)

try:
    # Get a sound's details.
    api_response = api_instance.sounds_sound_id_get(sound_id, x_asterisk_id=x_asterisk_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling SoundsApi->sounds_sound_id_get: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **sound_id** | **str**| Sound&#39;s id | 
 **x_asterisk_id** | **str**| Asterisk ID used to route the request through the API Gateway | [optional] 

### Return type

[**Sound**](Sound.md)

### Authorization

[basicAuth](../README.md#basicAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: Not defined

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

