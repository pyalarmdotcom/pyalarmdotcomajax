# Alarm.com Python Library

version number: 0.2.0

author: Justin Wong

## Overview

A Python library to asynchronously interface with Alarm.com.
Forked from Daren Lord's pyalarmdotcom. Mainly built for use with Home-Assistant.

## Installation / Usage

To install use pip:

```bash
pip install pyalarmdotcomajax
```

Or clone the repo:

```bash
git clone https://github.com/uvjustin/pyalarmdotcomajax.git
python setup.py install
```

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

### Known Sensor deviceTypes

This list identifies deviceTypes used in the alarm.com API and is incomplete. Please help by submitting missing values.

| deviceType | Description          |
|------------|----------------------|
| 1          | Contact Sensor       |
| 5          | Smoke Detector       |
| 6          | CO Detector          |
| 9          | Panic Button         |
| 19         | Glass Break Detector |

## Command Line Interface

```bash
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

### VS Code Support Structures

This repository includes a full development environment for VS Code:

1. VS Code [dev container](https://code.visualstudio.com/docs/remote/create-dev-container). Automatically installs extensions and Python dependencies and registers Git pre-commit scripts.
2. Configuration files for type checking ([mypy](http://mypy-lang.org/)), linting ([flake8](https://flake8.pycqa.org/en/latest/), [isort](https://github.com/PyCQA/isort), and [black](https://github.com/psf/black)), and code security ([Bandit](https://bandit.readthedocs.io/en/latest/)).
3. Pre-commit checks run all of the above when committing to Git and on demand via VS Code [tasks](https://code.visualstudio.com/docs/editor/tasks).

### References

1. Some API definitions are available in the [node-alarm-dot-com repository](https://github.com/node-alarm-dot-com/node-alarm-dot-com/tree/master/src/_models).

### Open Items

1. Support additional components (thermostats, irrigation, etc.).
2. Support more sensor types (see list above in this README).
3. Add `debug_info` property to `ADCController` that returns aggregate of raw JSON from all endpoints. This will allow users to export the entity model of unsupported devices to help maintainers implement support in this library.
4. Similar to above, proactively populate `unsupported_devices` property for `ADCBaseElement` to show users device id, device name, and device type for available but unsupported devices.
5. More granular exception handling when logging in. Should report discrete error types for authentication failures due to wrong credentials, connection issues, or other.
