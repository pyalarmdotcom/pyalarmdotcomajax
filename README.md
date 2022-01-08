# Alarm.com Python Library

version number: 0.2.0

author: Justin Wong

## Overview

A Python library to asynchronously interface with Alarm.com.
Forked from Daren Lord's pyalarmdotcom. Mainly built for use with Home-Assistant.

## Installation / Usage

To install use pip:

    $ pip install pyalarmdotcomajax


Or clone the repo:

    $ git clone https://github.com/uvjustin/pyalarmdotcomajax.git
    $ python setup.py install

## Usage

See `examples/basic_sensor_data.py` for a basic usage example.

## Device Support

- As of v0.2.0, multiples of all devices are supported.
- All devices include the attributes: `name`, `id_`, `state`, `battery_low`, `battery_critical`, `malfunctioning`, `parent_ids`, and a few others.


|Device Type|Notable Attributes|Actions|
|--|--|--|
|System|`unit_id`|(none)|
|Partition|`uncleared_issues`, `desired_state`|arm away, arm stay, arm night, disarm
|Sensors|`device_subtype`|(none)|
|Locks|`desired_state`|lock, unlock|
|Garage Door|(none)|open, close|

## Command Line Interface

```
python -m pyalarmdotcomajax

usage: __main__.py [-h] -u USERNAME -p PASSWORD [-c COOKIE] [-x {ADT,Protection1,Other}] [-ver]

Basic command line interface for Alarm.com

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        alarm.com username
  -p PASSWORD, --password PASSWORD
                        alarm.com password
  -c COOKIE, --cookie COOKIE
                        two-factor authentication cookie
  -x {ADT,Protection1,Other}, --provider {ADT,Protection1,Other}
                        alarm.com service provider (default: Other)
  -ver, --version       show program's version number and exit
```

## Development

### Sensor deviceTypes

This list identifies deviceTypes used in the alarm.com API and is incomplete. Please help by submitting missing values.

| deviceType | Description          |
|------------|----------------------|
| 1          | Contact Sensor       |
| 5          | Smoke Detector       |
| 6          | CO Detector          |
| 9          | Panic Button         |
| 19         | Glass Break Detector |