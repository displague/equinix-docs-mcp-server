# Spec vetting report

689 tools OK, 1 failures, 6 not discoverable by exact-name search.

| family | ok | failed |
|---|---|---|
| access | 39 | 0 |
| accesstoken | 2 | 0 |
| assets | 2 | 0 |
| attachments | 5 | 0 |
| bas | 3 | 0 |
| billing | 2 | 0 |
| billingv1 | 3 | 0 |
| crossconnects | 3 | 0 |
| diloa | 14 | 0 |
| fabric | 194 | 0 |
| getprojects | 1 | 0 |
| internetaccess | 27 | 0 |
| internetaccessv2 | 6 | 0 |
| lookup | 5 | 0 |
| metal | 218 | 1 |
| network-edge | 54 | 0 |
| notifications | 4 | 0 |
| orderhistory | 2 | 0 |
| orders | 5 | 0 |
| quotes | 1 | 0 |
| reports | 13 | 0 |
| securecabinet | 2 | 0 |
| shipments | 4 | 0 |
| shipmentsv2 | 2 | 0 |
| smarthands | 14 | 0 |
| smartview | 33 | 0 |
| sts | 10 | 0 |
| support | 7 | 0 |
| supportplans | 1 | 0 |
| tickets | 5 | 0 |
| troubleticket | 3 | 0 |
| unifiednotification | 1 | 0 |
| workvisit | 4 | 0 |

## Failure categories
- other: 1

## Failures by family
### metal
- `metal_updateBgpSession` [other]: Error calling tool 'metal_updateBgpSession': Error building request for PUT /metal/v1/bgp/sessions/{id}: TypeError: Unexpected type for 'content', <class 'bool'>

## Not discoverable via search_tools (exact name query)
- `metal_createDevice`
- `network-edge_createVirtualDevice`
- `network-edge_createVirtualDeviceByUuid`
- `network-edge_updateVirtualDeviceByUuid`
- `network-edge_createDeviceRMAByUuid`
- `smartview_getAlerts`
