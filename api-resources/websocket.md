# Light Turns On


```json
{
    "EventDateUtc": "2023-03-28T15:07:43.71Z",
    "UnitId": 103238342,
    "DeviceId": 1216,
    "EventType": 315,
    "EventValue": 255.0,
    "CorrelatedId": null,
    "QstringForExtraData": null
}
```

```json
{
    "EventDateUtc": "2023-03-28T15:07:43.71Z",
    "UnitId": 103238342,
    "DeviceId": 1216,
    "NewState": 1,
    "FlagMask": 1
}
```


# Light Turns Off:


```json
{
    "EventDateUtc": "2023-03-28T15:07:46.728Z",
    "UnitId": 103238342,
    "DeviceId": 1216,
    "EventType": 316,
    "EventValue": 0.0,
    "CorrelatedId": null,
    "QstringForExtraData": null
}
```

```json
{
    "EventDateUtc": "2023-03-28T15:07:46.728Z",
    "UnitId": 103238342,
    "DeviceId": 1216,
    "NewState": 0,
    "FlagMask": 1
}
```

# User Logs In


```json
{
    "EventDateUtc": "2023-05-09T19:59:11.026Z",
    "UnitId": 103238342,
    "DeviceId": 127,
    "EventType": 55,
    "EventValue": 15669399.0,
    "CorrelatedId": 15669399,
    "QstringForExtraData": "ln=USERNAME&ip=IP.ADD.RESS&src=1&mrid=",
    "DeviceType": -1
}
```

# Contact Sensor Opens

Front door

Monitoring Event

```json
{
    "EventDateUtc": "2023-05-09T20:01:16.506Z",
    "UnitId": 103238342,
    "DeviceId": 7,
    "EventType": 15,
    "EventValue": 0.0,
    "CorrelatedId": null,
    "QstringForExtraData": "openClosedStatusWord=open",
    "DeviceType": 1
}
```

# Contact Sensor Closes

Front door

Monitoring Event

```json
{
    "EventDateUtc": "2023-05-09T20:08:08.158Z",
    "UnitId": 103238342,
    "DeviceId": 7,
    "EventType": 0,
    "EventValue": 0.0,
    "CorrelatedId": null,
    "QstringForExtraData": "openClosedStatusWord=closed",
    "DeviceType": 1
}
```

# Contact Sensor Open/Closed

```json
{
    "EventDateUtc": "2023-05-11T00:29:25.438Z",
    "UnitId": 103238342,
    "DeviceId": 7,
    "EventType": 100,
    "EventValue": 0.0,
    "CorrelatedId": null,
    "QstringForExtraData": null,
    "DeviceType": 1
}
```

# Door Left Open Notification

2023-06-08 00:33:44.512 DEBUG (MainThread) [pyalarmdotcomajax.websockets.client]
====================[ WEBSOCKET MESSAGE: BEGIN ]====================

```json
{
    "EventDateUtc": "2023-06-08T00:33:44.661Z",
    "UnitId": 103238342,
    "DeviceId": 7,
    "EventType": 101,
    "EventValue": 1.0,
    "CorrelatedId": null,
    "QstringForExtraData": null,
    "DeviceType": -1
}
```
2023-06-08 00:33:44.513 DEBUG (MainThread) [pyalarmdotcomajax.websockets.messages] WebSocket Message Type: Event

2023-06-08 00:33:44.514 DEBUG (MainThread) [pyalarmdotcomajax.websockets.handler.sensor] Support for event EventType.DoorLeftOpen (101) not yet implemented by Sensor.

# Door Closed After Being Left Open

2023-06-07 20:38:05.127 DEBUG (MainThread) [pyalarmdotcomajax.devices] Desired: [1] | Current: [1]

2023-06-07 20:38:05.127 DEBUG (MainThread) [pyalarmdotcomajax.websockets.client]

====================[ WEBSOCKET MESSAGE: END ]====================

2023-06-07 20:38:05.129 DEBUG (MainThread) [pyalarmdotcomajax.websockets.client]

====================[ WEBSOCKET MESSAGE: BEGIN ]====================

```json
{
    "EventDateUtc": "2023-06-07T20:38:05.334Z",
    "UnitId": 103238342,
    "DeviceId": 7,
    "EventType": 103,
    "EventValue": 1.0,
    "CorrelatedId": null,
    "QstringForExtraData": null,
    "DeviceType": -1
}
```
2023-06-07 20:38:05.129 DEBUG (MainThread) [pyalarmdotcomajax.websockets.messages] WebSocket Message Type: Event

2023-06-07 20:38:05.130 DEBUG (MainThread) [pyalarmdotcomajax.websockets.handler.sensor] Support for event EventType.DoorLeftOpenRestoral (103) not yet implemented by Sensor.

2023-06-07 20:38:05.130 DEBUG (MainThread) [pyalarmdotcomajax.websockets.client]

# Front Porch On

State Change

Show new state

```json
{
    "EventDateUtc": "2023-05-09T20:02:51.741Z",
    "UnitId": 103238342,
    "DeviceId": 1200,
    "NewState": 1,
    "FlagMask": 1
}
```

Monitoring Event

Shows brightness

Dimmers use 317 for on (brightness changed), on/off switches use 315 (light turned on)

```json
{
    "EventDateUtc": "2023-05-09T20:02:51.741Z",
    "UnitId": 103238342,
    "DeviceId": 1200,
    "EventType": 317,
    "EventValue": 99.0,
    "CorrelatedId": null,
    "QstringForExtraData": null,
    "DeviceType": -1
}
```

# Front Porch Off

Monitoring Event

```json
{
    "EventDateUtc": "2023-05-09T20:03:04.722Z",
    "UnitId": 103238342,
    "DeviceId": 1200,
    "NewState": 0,
    "FlagMask": 1
}
```

State Change

```json
{
    "EventDateUtc": "2023-05-09T20:03:04.722Z",
    "UnitId": 103238342,
    "DeviceId": 1200,
    "EventType": 316,
    "EventValue": 0.0,
    "CorrelatedId": null,
    "QstringForExtraData": null,
    "DeviceType": -1
}
```


# Thermostat Ambient Temperature Periodic Report

Property change

Inside temperature was 72F. Setpoint was 73F. This may be outdoor temp.
```json
{
    "ChangeDateUtc": "2023-05-09T20:14:00.944Z",
    "UnitId": 103238342,
    "DeviceId": 2207,
    "Property": 1,
    "PropertyValue": 6660,
    "ReportedDateUtc": "2023-05-09T20:14:00.944Z",
    "QstringForExtraData": "tempC=1922.00"
}
```

# Thermostat Cool Change Setpoint from 73 to 74

Property Change (Heat Setpoint)

```json
{
    "ChangeDateUtc": "2023-05-09T20:20:59.779Z",
    "UnitId": 103238342,
    "DeviceId": 2207,
    "Property": 2,
    "PropertyValue": 6800,
    "ReportedDateUtc": "2023-05-09T20:20:59.779Z",
    "QstringForExtraData": "tempC=2000"
}
```

Property Change (Cool Setpoint)

```json
{
    "ChangeDateUtc": "2023-05-09T20:20:59.779Z",
    "UnitId": 103238342,
    "DeviceId": 2207,
    "Property": 3,
    "PropertyValue": 7400,
    "ReportedDateUtc": "2023-05-09T20:20:59.779Z",
    "QstringForExtraData": "tempC=2333.00"
}
```

Property Change (Ambient)

```json
{
    "ChangeDateUtc": "2023-05-09T20:20:59.779Z",
    "UnitId": 103238342,
    "DeviceId": 2207,
    "Property": 1,
    "PropertyValue": 7170,
    "ReportedDateUtc": "2023-05-09T20:20:59.779Z",
    "QstringForExtraData": "tempC=2206.00"
}
```


