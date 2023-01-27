<p align="center"><img src="https://user-images.githubusercontent.com/466460/175575400-44ab6ed5-acb4-4a8c-b2ab-8b757675e900.png" height="200px"></p>
<h1 align="center" border="1px solid black">pyalarmdotcomajax</h1>
<h3 align="center">Asynchronous Python Library for Accessing Alarm.com Services</h3>
<p align="center">This is an unofficial project that is not affiliated with Alarm.com.</p>
<p align="center"><em>Forked from Daren Lord's pyalarmdotcom.</em></p>
<br />
<p align="center">
  <a href="https://github.com/uvjustin"><img src="https://img.shields.io/badge/Creator-Justin%20Wong%20(%40uvjustin)-blue" /></a>
  <a href="https://github.com/elahd"><img src="https://img.shields.io/badge/Maintainer-Elahd%20Bar--Shai%20(%40elahd)-blue" /></a>
</p>
<p align="center">
  <a href="https://www.codacy.com/gh/pyalarmdotcom/pyalarmdotcomajax/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyalarmdotcom/pyalarmdotcomajax&amp;utm_campaign=Badge_Grade"><img src="https://app.codacy.com/project/badge/Grade/c58b00c68f9542aea1554d160997e5cd"/></a>
  <a href="https://www.codacy.com/gh/pyalarmdotcom/pyalarmdotcomajax/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyalarmdotcom/pyalarmdotcomajax&amp;utm_campaign=Badge_Coverage"><img src="https://app.codacy.com/project/badge/Coverage/c58b00c68f9542aea1554d160997e5cd"/></a>
  <a href="https://results.pre-commit.ci/latest/github/pyalarmdotcom/pyalarmdotcomajax/master"><img src="https://results.pre-commit.ci/badge/github/pyalarmdotcom/pyalarmdotcomajax/master.svg" /></a>
  <a href="https://pypi.org/project/pyalarmdotcomajax/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pyalarmdotcomajax"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
  <a href="https://github.com/PyCQA/pylint"><img src="https://img.shields.io/badge/linting-pylint-yellowgreen" /></a>
  <a href="https://github.com/pyalarmdotcom/pyalarmdotcomajax/blob/master/LICENSE"><img alt="GitHub" src="https://img.shields.io/github/license/pyalarmdotcom/pyalarmdotcomajax"></a>
</p>

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

| Device Type  | Notable Attributes                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Actions                               | Notes                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------ |
| System       | `unit_id`                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | (none)                                |                                                  |
| Partition    | `uncleared_issues`, `desired_state`                                                                                                                                                                                                                                                                                                                                                                                                                                       | arm away, arm stay, arm night, disarm |                                                  |
| Sensor       | `device_subtype`                                                                                                                                                                                                                                                                                                                                                                                                                                                          | (none)                                |                                                  |
| Locks        | `desired_state`                                                                                                                                                                                                                                                                                                                                                                                                                                                           | lock, unlock                          |                                                  |
| Garage Door  | (none)                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | open, close                           |                                                  |
| Gate         | `supports_remote_close`                                                                                                                                                                                                                                                                                                                                                                                                                                                   | open, close                           |                                                  |
| Image Sensor | `images`                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | peek_in                               |                                                  |
| Light        | `brightness`                                                                                                                                                                                                                                                                                                                                                                                                                                                              | turn_on (with brightness), turn_off   | No support for RGB/W, effects, temperature, etc. |
| Thermostat   | `temp_average`, `temp_at_tstat`, `step_value`, `supports_fan_mode`, `supports_fan_indefinite`, `supports_fan_circulate_when_off`, `supported_fan_durations`, `fan_mode`, `supports_heat`, `supports_heat_aux`, `supports_cool`, `supports_auto`, `min_heat_setpoint`, `min_cool_setpoint`, `max_heat_setpoint`, `max_cool_setpoint`, `heat_setpoint`, `cool_setpoint`, `supports_humidity`, `humidity`, `supports_schedules`, `supports_schedules_smart`, `schedule_mode` | set_attribute                         |                                                  |
| Water Sensor |                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | (none)                                |                                                  |

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
| 52         | Vibration Contact Sensor               |
| 68         | Panel Image Sensor                     |
| 69         | Mobile Phone (for Bluetooth Disarming) |
| 83         | Panel Glass Break Sensor               |
| 89         | Panel Motion Sensor                    |

## Device Support (Configuration)

Pyalarmdotcomajax supports changing configuration options for the devices listed below.

### Skybell HD

#### Doorbell Camera

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

get options:
  -h, --help            show this help message and exit
  -x, --include-unsupported
                        return basic data for all known unsupported devices. always outputs in verbose format.

set options:
  -h, --help            show this help message and exit
  -i DEVICE_ID, --device-id DEVICE_ID
                        Numeric Alarm.com device identifier.
  -s SETTING_SLUG, --setting-slug SETTING_SLUG
                        Identifier for setting. Appears in parenthesis after setting name in adc set human readable output.
  -k NEW_VALUE, --new-value NEW_VALUE
                        New value for setting.
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
