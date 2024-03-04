"""Alarm.com model for lights."""

from dataclasses import dataclass, field
from enum import Enum

from pyalarmdotcomajax.models.base import (
    AdcDeviceResource,
    AdcResourceAttributes,
    BaseManagedDeviceAttributes,
    ResourceType,
)


class LightState(Enum):
    """Light states."""

    OFFLINE = 0
    NO_STATE = 1
    ON = 2
    OFF = 3
    LEVEL_CHANGE = 4


class LightColorFormat(Enum):
    """Light color formats."""

    NOT_SET = 0
    RGBW = 1
    RGB = 2
    WARM_TO_COOL = 3
    HSV = 4


@dataclass
class LightAttributes(BaseManagedDeviceAttributes[LightState], AdcResourceAttributes):
    """Attributes of light."""

    # fmt: off
    can_enable_remote_commands: bool = field(metadata={"description": "Can the remote commands be enabled or disabled?"})
    can_enable_state_tracking: bool = field(metadata={"description": "Can state tracking be enabled for this light?"})
    hex_color: str | None = field(metadata={"description": "A hex string representing the currently active color. For decoding this should be used in conjunction with 'lightColorFormat'."})
    is_dimmer: bool = field(metadata={"description": "Is the light a dimmer?"})
    light_color_format: LightColorFormat = field(metadata={"description": "The format of the color hex string. This values maps in the LightColorFormat enum. Defaults to 'Not Set'."})
    light_level: int = field(metadata={"description": "Dimmer value for a dimmer light"})
    percent_warmth: int = field(metadata={"description": "Represents a percentage from 0-100, the color temperature is between the minimum (cool) and maximum (100% warm) temperatures we support."})
    remote_commands_enabled: bool = field(metadata={"description": "Whether remote commands are enabled or not."})
    state_tracking_enabled: bool = field(metadata={"description": "Is state tracking enabled?"})
    supports_rgb_color_control: bool = field(metadata={"description": "Does it support RGB color changing?"})
    supports_white_light_color_control: bool = field(metadata={"description": "Does it support color temperature changing? (Selecting between variations of white light)."})

    # is_favorite: bool = field(metadata={"description": "Is the light in the Favorites Group?"})
    # is_zwave: bool = field(metadata={"description": "Is the light a ZWave device."})
    # light_groups: bool = field(metadata={"description": "Light groups that this light belongs to"})
    # should_show_favorites_toggle: bool = field(metadata={"description": "Should the 'Favorites' toggle be shown in the edit light modal?"})
    # should_update_multi_level_state: bool = field(metadata={"description": "Whether or not we should update multilevel state as part of saving this model. Used to avoid turning on a multilevel light when updating non-lighting properties such as device name"})
    # fmt: on

    @property
    def supports_color_control(self) -> bool:
        """Whether the light supports color control."""

        return self.supports_rgb_color_control or self.supports_white_light_color_control


@dataclass
class Light(AdcDeviceResource[LightAttributes]):
    """Light resource."""

    resource_type = ResourceType.LIGHT
    attributes_type = LightAttributes
