# BridgeAttendedTransfer

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**destination_application** | **str** | Application that has been transferred into | [optional] 
**destination_bridge** | **str** | Bridge that survived the merge result | [optional] 
**destination_link_first_leg** | [**Channel**](Channel.md) | First leg of a link transfer result | [optional] 
**destination_link_second_leg** | [**Channel**](Channel.md) | Second leg of a link transfer result | [optional] 
**destination_threeway_bridge** | [**Bridge**](Bridge.md) | Bridge that survived the threeway result | [optional] 
**destination_threeway_channel** | [**Channel**](Channel.md) | Transferer channel that survived the threeway result | [optional] 
**destination_type** | **str** | How the transfer was accomplished | 
**is_external** | **bool** | Whether the transfer was externally initiated or not | 
**replace_channel** | [**Channel**](Channel.md) | The channel that is replacing transferer_first_leg in the swap | [optional] 
**result** | **str** | The result of the transfer attempt | 
**transfer_target** | [**Channel**](Channel.md) | The channel that is being transferred to | [optional] 
**transferee** | [**Channel**](Channel.md) | The channel that is being transferred | [optional] 
**transferer_first_leg** | [**Channel**](Channel.md) | First leg of the transferer | 
**transferer_first_leg_bridge** | [**Bridge**](Bridge.md) | Bridge the transferer first leg is in | [optional] 
**transferer_second_leg** | [**Channel**](Channel.md) | Second leg of the transferer | 
**transferer_second_leg_bridge** | [**Bridge**](Bridge.md) | Bridge the transferer second leg is in | [optional] 

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


