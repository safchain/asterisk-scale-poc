# LiveRecording

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**cause** | **str** | Cause for recording failure if failed | [optional] 
**duration** | **int** | Duration in seconds of the recording | [optional] 
**format** | **str** | Recording format (wav, gsm, etc.) | 
**name** | **str** | Base name for the recording | 
**silence_duration** | **int** | Duration of silence, in seconds, detected in the recording. This is only available if the recording was initiated with a non-zero maxSilenceSeconds. | [optional] 
**state** | **str** |  | 
**talking_duration** | **int** | Duration of talking, in seconds, detected in the recording. This is only available if the recording was initiated with a non-zero maxSilenceSeconds. | [optional] 
**target_uri** | **str** | URI for the channel or bridge being recorded | 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


