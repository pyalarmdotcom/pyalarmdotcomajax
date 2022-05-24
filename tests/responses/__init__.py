"""Load responses from JSON files."""

from importlib import resources

SENSORS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "sensor_ok.json",
)

CAMERAS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "camera_ok.json",
)

GARAGE_DOORS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "garage_door_ok.json",
)

IDENTITYS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "identity_ok.json",
)

IMAGE_SENSORS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "image_sensor_ok.json",
)

IMAGE_SENSORS_DATA_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "image_sensor_data_ok.json",
)

LIGHTS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "light_ok.json",
)

LOCKS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "lock_ok.json",
)

PARTITIONS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "partition_ok.json",
)

SYSTEMS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "system_ok.json",
)

TROUBLE_CONDITIONS_OK_RESPONSE_BODY = resources.read_text(
    __package__,
    "trouble_condition_ok.json",
)

SKYBELL_CONFIG_PAGE = resources.read_text(
    __package__,
    "camera_settings_skybell.html",
)

SKYBELL_CONFIG_PAGE_CHANGED = resources.read_text(
    __package__,
    "camera_settings_skybell_changed.html",
)
