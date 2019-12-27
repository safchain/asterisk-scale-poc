# TextMessage

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**body** | **str** | The text of the message. | 
**_from** | **str** | A technology specific URI specifying the source of the message. For sip and pjsip technologies, any SIP URI can be specified. For xmpp, the URI must correspond to the client connection being used to send the message. | 
**to** | **str** | A technology specific URI specifying the destination of the message. Valid technologies include sip, pjsip, and xmp. The destination of a message should be an endpoint. | 
**variables** | [**list[TextMessageVariable]**](TextMessageVariable.md) | Technology specific key/value pairs associated with the message. | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


