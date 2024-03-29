<p align="center"><img src="https://user-images.githubusercontent.com/466460/175575400-44ab6ed5-acb4-4a8c-b2ab-8b757675e900.png" height="200px"></p>
<h1 align="center" border="1px solid black">pyalarmdotcomajax</h1>
<h3 align="center">Asynchronous, Event-Driven Python Library for Accessing Alarm.com Services</h3>
<p align="center">This is an unofficial project that is not affiliated with Alarm.com.</p>
<p align="center"><em>Forked from Daren Lord's pyalarmdotcom.</em></p>
<br />
<p align="center">
  <a href="https://github.com/uvjustin"><img src="https://img.shields.io/badge/Creator-Justin%20Wong%20(%40uvjustin)-blue" /></a>
  <a href="https://github.com/elahd"><img src="https://img.shields.io/badge/Maintainer-Elahd%20Bar--Shai%20(%40elahd)-blue" /></a>
</p>
<p align="center">
  <!-- <a href="https://www.codacy.com/gh/pyalarmdotcom/pyalarmdotcomajax/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyalarmdotcom/pyalarmdotcomajax&amp;utm_campaign=Badge_Grade"><img src="https://app.codacy.com/project/badge/Grade/c58b00c68f9542aea1554d160997e5cd"/></a> -->
  <!-- <a href="https://www.codacy.com/gh/pyalarmdotcom/pyalarmdotcomajax/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=pyalarmdotcom/pyalarmdotcomajax&amp;utm_campaign=Badge_Coverage"><img src="https://app.codacy.com/project/badge/Coverage/c58b00c68f9542aea1554d160997e5cd"/></a> -->
  <a href="https://results.pre-commit.ci/latest/github/pyalarmdotcom/pyalarmdotcomajax/master"><img src="https://results.pre-commit.ci/badge/github/pyalarmdotcom/pyalarmdotcomajax/master.svg" /></a>
  <a href="https://pypi.org/project/pyalarmdotcomajax/"><img alt="PyPI" src="https://img.shields.io/pypi/v/pyalarmdotcomajax"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
  <a href="https://github.com/charliermarsh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json" /></a>
  <a href="https://github.com/pyalarmdotcom/pyalarmdotcomajax/blob/master/LICENSE"><img alt="GitHub" src="https://img.shields.io/github/license/pyalarmdotcom/pyalarmdotcomajax" /></a>
</p>

## Installation / Usage

To install use pip:

```bash
pip install pyalarmdotcomajax
```

Or clone the repo:

```bash
git clone https://github.com/pyalarmdotcomajax/pyalarmdotcomajax.git
cd pyalarmdotcomajax
pip install .
```

## Usage

See `examples/basic_sensor_data.py` for a basic usage example.

## Device Support (Core Functions)

Pyalarmdotcomajax supports core features (monitoring and using actions) of the device types listed below.

| Device Type  | Actions                                                 | Notes                                                                                                                                                                                                                                                                                                                   |
| ------------ | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Garage Door  | open, close                                             |                                                                                                                                                                                                                                                                                                                         |
| Gate         | open, close                                             |                                                                                                                                                                                                                                                                                                                         |
| Image Sensor | peek_in                                                 |                                                                                                                                                                                                                                                                                                                         |
| Light        | turn_on (with brightness), turn_off                     | No support for RGB/W, effects, temperature, etc.                                                                                                                                                                                                                                                                        |
| Locks        | lock, unlock                                            |                                                                                                                                                                                                                                                                                                                         |
| Partition    | clear faults, arm away, arm stay, arm night, disarm     |                                                                                                                                                                                                                                                                                                                         |
| Sensor       | bypass/unbypass (via partition)                         | Contact sensors will not report the same state within a 3-minute window. This means that this library will only show one event if, say, a door has been opened and closed multiple times within 3 minutes. See (this post)[https://support.suretyhome.com/t/alarm-com-3-minute-deduplication-window/24637] for details. |
| System       | stop alarms, clear smoke sensor, clear alarms in memory |                                                                                                                                                                                                                                                                                                                         |
| Thermostat   | set attributes                                          |                                                                                                                                                                                                                                                                                                                         |
| Water Sensor | (none)                                                  |                                                                                                                                                                                                                                                                                                                         |

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

Skybell HD configuration support not yet implemented in v6 beta.

## Command Line Interface

The CLI is available by running `adc` from anywhere in your terminal. Use `adc --help` for more information.

Detailed helptext for the CLI is also available [here](pyalarmdotcomajax/adc/README.md).

## Development

### VS Code Support Structures

This repository includes a full development environment for VS Code:

1. VS Code [dev container](https://code.visualstudio.com/docs/remote/create-dev-container). Automatically installs extensions and Python dependencies and registers Git pre-commit scripts.
2. Configuration files for type checking ([mypy](http://mypy-lang.org/)), linting & formatting ([ruff](https://github.com/astral-sh/ruff), etc.
3. Pre-commit checks run all of the above when committing to Git and on demand via VS Code [tasks](https://code.visualstudio.com/docs/editor/tasks).

### Open Items

#### Features

1. Support additional components (light RGBW, irrigation, etc.).
2. Support more sensor types (see list above in this README).
3. Add `debug_info` property to `ADCController` that returns aggregate of raw JSON from all endpoints. This will allow users to export the entity model of unsupported devices to help maintainers implement support in this library.
