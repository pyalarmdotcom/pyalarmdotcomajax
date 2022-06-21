# Alarm.com Python Library

**Author: Justin Wong**

**Maintainer: Elahd Bar-Shai**

## Overview

A Python library to asynchronously interface with Alarm.com.
Forked from Daren Lord's pyalarmdotcom. Mainly built for use with Home Assistant.

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

## Device Support (Core Functions)

Pyalarmdotcomajax supports core features (monitoring and using actions) of the device types listed below.

- As of v0.2, multiples of all devices are supported.
- All devices include the attributes: `name`, `id_`, `state`, `battery_low`, `battery_critical`, `malfunctioning`, `parent_ids`, and a few others.

| Device Type  | Notable Attributes                  | Actions                               | Notes                                            |
| ------------ | ----------------------------------- | ------------------------------------- | ------------------------------------------------ |
| System       | `unit_id`                           | (none)                                |                                                  |
| Partition    | `uncleared_issues`, `desired_state` | arm away, arm stay, arm night, disarm |                                                  |
| Sensor       | `device_subtype`                    | (none)                                |                                                  |
| Locks        | `desired_state`                     | lock, unlock                          |                                                  |
| Garage Door  | (none)                              | open, close                           |                                                  |
| Image Sensor | `images`                            | peek_in                               |                                                  |
| Light        | `brightness`                        | turn_on (with brightness), turn_off   | No support for RGB/W, effects, temperature, etc. |

### Known Sensor deviceTypes

This list identifies deviceTypes used in the alarm.com API and is incomplete. Please help by submitting missing values.

| deviceType | Description                            |
| ---------- | -------------------------------------- |
| 1          | Contact Sensor                         |
| 2          | Motion Sensor                          |
| 5          | Smoke Detector                         |
| 6          | CO Detector                            |
| 8          | Freeze Sensor                          |
| 9          | Panic Button                           |
| 10         | Fixed Panic Button                     |
| 14         | Siren                                  |
| 19         | Glass Break Detector                   |
| 52         | Contact/Shock Sensor                   |
| 68         | Panel Image Sensor                     |
| 69         | Mobile Phone (for Bluetooth Disarming) |
| 83         | Panel Glass Break Sensor               |
| 89         | Panel Motion Sensor                    |

## Device Support (Configuration)

Pyalarmdotcomajax supports changing configuration options for the devices listed below.

### Skybell HD

**Doorbell Camera**

| Configuration Option      | Slug                 | Supported Values                     | Notes                      |
| ------------------------- | -------------------- | ------------------------------------ | -------------------------- |
| Indoor Chime              | `indoor-chime`       | `on`, `off`                          |                            |
| Outdoor Chime             | `outdoor-chime`      | `off`, `low`, `medium`, `high`       |                            |
| LED Brightness            | `led-brightness`     | 0-100                                |                            |
| LED Color                 | `led-color`          | `#000000` - `#FFFFFF`                | Must include `#` at start. |
| Motion Sensor Sensitivity | `motion-sensitivity` | `low`, `medium`, `high`, `very_high` |                            |

## Command Line Interface

The CLI is available by running `adc` from anywhere in your terminal. Use `adc --help`, `adc get --help`, and `adc set --help` for more information.

```bash
usage: adc [-h] [-d] [-ver] [-v] -u USERNAME -p PASSWORD [-n DEVICE_NAME] [-c COOKIE | -o ONE_TIME_PASSWORD] {get,set} ...

basic command line debug interface for alarm.com via pyalarmdotcomajax. shows device states in various formats.

options:
  -h, --help            show this help message and exit
  -d, --debug           show pyalarmdotcomajax's debug output.
  -ver, --version       show program's version number and exit
  -v, --verbose         show verbose output. -vv returns base64 image data for image sensor images.
  -u USERNAME, --username USERNAME
                        alarm.com username
  -p PASSWORD, --password PASSWORD
                        alarm.com password
  -n DEVICE_NAME, --device-name DEVICE_NAME
                        registers a device with this name on alarm.com and requests the two-factor authentication cookie for the device.
  -c COOKIE, --cookie COOKIE
                        two-factor authentication cookie. cannot be used with --one-time-password!
  -o ONE_TIME_PASSWORD, --one-time-password ONE_TIME_PASSWORD
                        provide otp code for accounts that have two-factor authentication enabled. if not provided here, adc will prompt user for otp. cannot be used with --cookie!

actions:
  {get,set}
    get                 get data from alarm.com. use 'adc get --help' for parameters.
    set                 set device configuration option. use 'adc set --help' for parameters
```

### Examples

1. Get human-readable status (and device IDs) for all devices: `adc -u "your_username" -p "your_password" get`
2. Get raw JSON output from Alarm.com for all devices: `adc -v -u "your_username" -p "your_password" get`
3. Turn off Skybell HD indoor chime (assume Skybell device ID is 283431032-1520): `adc -u "your_username" -p "your_password" set -i "283431032-1520" -s "indoor-chime" -k "off"`

## Development

### VS Code Support Structures

This repository includes a full development environment for VS Code:

1. VS Code [dev container](https://code.visualstudio.com/docs/remote/create-dev-container). Automatically installs extensions and Python dependencies and registers Git pre-commit scripts.
2. Configuration files for type checking ([mypy](http://mypy-lang.org/)), linting ([flake8](https://flake8.pycqa.org/en/latest/), [isort](https://github.com/PyCQA/isort), and [black](https://github.com/psf/black)), code security ([Bandit](https://bandit.readthedocs.io/en/latest/)), etc.
3. Pre-commit checks run all of the above when committing to Git and on demand via VS Code [tasks](https://code.visualstudio.com/docs/editor/tasks).

### References

1. Some API definitions are available in the [node-alarm-dot-com repository](https://github.com/node-alarm-dot-com/node-alarm-dot-com/tree/master/src/_models).

### Open Items

#### Features

1. Support additional components (lights, irrigation, etc.).
2. Support more sensor types (see list above in this README).
3. Add `debug_info` property to `ADCController` that returns aggregate of raw JSON from all endpoints. This will allow users to export the entity model of unsupported devices to help maintainers implement support in this library.
4. Similar to above, proactively populate `unsupported_devices` property for `ADCBaseElement` to show users device id, device name, and device type for available but unsupported devices.
5. More granular exception handling when logging in. Should report discrete error types for authentication failures due to wrong credentials, connection issues, or other.

#### Housekeeping

1. Testing framework

[license-shield]: https://img.shields.io/github/license/uvjustin/pyalarmdotcomajax.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/uvjustin/pyalarmdotcomajax.svg?style=for-the-badge
[releases]: https://github.com/uvjustin/pyalarmdotcomajax/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/uvjustin/pyalarmdotcomajax.svg?style=for-the-badge
[commits]: https://github.com/uvjustin/pyalarmdotcomajax/commits/master
