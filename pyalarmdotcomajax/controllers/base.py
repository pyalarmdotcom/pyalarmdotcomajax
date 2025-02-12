"""Base controller for Ember.js/JSON:API based components."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import ABC
from asyncio import Task, iscoroutinefunction
from collections.abc import Awaitable, Callable, Iterator
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from rich.console import Group

from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE
from pyalarmdotcomajax.events import EventBrokerMessage, EventBrokerTopic, ResourceEventMessage
from pyalarmdotcomajax.exceptions import UnknownDevice
from pyalarmdotcomajax.models import AdcResourceT
from pyalarmdotcomajax.util import resources_pretty, resources_raw
from pyalarmdotcomajax.websocket.client import RawResourceEventMessage, SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import BaseWSMessage, EventWSMessage, ResourceEventType

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge
    from pyalarmdotcomajax.models.base import ResourceType
    from pyalarmdotcomajax.models.jsonapi import Resource

log = logging.getLogger(__name__)


class BaseController(ABC, Generic[AdcResourceT]):
    """Base controller for Ember.js/JSON:API based components."""

    # ResourceTypes to be pulled from API response data object.
    resource_type: ClassVar[ResourceType]
    # AdcResource class to be created by this controller.
    _resource_class: type[AdcResourceT]
    # URL to be used for API requests when URL cannot be derived directly from controler's ResourceType.
    _resource_url_override: ClassVar[str | None] = None
    # Restricts this controller to specific device IDs.
    _requires_target_ids: ClassVar[bool] = False
    # WebSocket events supported by this controller.
    _supported_resource_events: ClassVar[SupportedResourceEvents | None] = None
    # Maps websocket events to states.
    _event_state_map: ClassVar[MappingProxyType[ResourceEventType, Enum] | None] = None

    def __init__(
        self,
        bridge: AlarmBridge,
        data_provider: BaseController | None = None,
        target_device_ids: list[str] | None = None,
    ) -> None:
        """Initialize base controller."""

        self._bridge = bridge

        if target_device_ids:
            self._target_device_ids.add(*target_device_ids)

        # Tracks whether the controller has been initialized.
        self._initialized: bool = False

        # Tracks primary resources discovered by this controller.
        self._resources: dict[str, AdcResourceT] = {}

        # Tracks included resources discovered by this controller.
        self._included_resources: list[Resource] = []

        # If set, the current controller will depend on the data provider for API fetch updates.
        self._api_data_provider = data_provider
        self._api_data_unsubscribe: Callable | None = None

        # Dict of callbacks for controllers that depend on the current controller for API updates.
        self._api_data_receivers: dict[ResourceType, list[Callable[[list[Resource]], Awaitable | None]]] = {}

        # Restricts this controller to specific devices. Used for controllers that only support single-serve endpoints.
        self._target_device_ids: set[str] = set({})

        # Holds references to asyncio tasks to prevent them from being garbage collected before completion.
        self._background_tasks: set[Task] = set()

    @property
    def items(self) -> list[AdcResourceT]:
        """Return all resources for this controller."""
        return list(self._resources.values())

    ##################
    # INITIALIZATION #
    ##################

    async def initialize(self, target_device_ids: list[str] | None = None) -> None:
        """
        Initialize controller.

        Controllers with a delegated API data provider should only be initialized by that data provider.
        """

        if self._initialized:
            return

        # Subscribe to WebSocket events if supported by controller.
        if self._supported_resource_events:
            self._bridge.events.subscribe(EventBrokerTopic.RAW_RESOURCE_EVENT, self._base_handle_event)

        # Bail now if we depend on another controller for API data.
        if self._api_data_provider:
            self._initialized = True
            self._api_data_unsubscribe = await self._api_data_provider.subcontroller_data_subscribe(
                [self.resource_type], self._refresh
            )
            return

        if target_device_ids:
            self._target_device_ids.add(*target_device_ids)

        await self._refresh()

    async def add_target(self, resource_id: str) -> AdcResourceT | None:
        """Add a device ID to the controller's list of targets."""

        await self._refresh(resource_id=resource_id)

        return self._resources.get(resource_id)

    #####################
    # DEVICE MANAGEMENT #
    #####################

    def _device_filter(self, response: list[Resource] | Resource) -> list[Resource] | Resource:
        """
        Filter out unsupported devices from API response.

        Intended to be overridden by child classes.
        """

        return response

    async def _send_command(self, id: str, action: str, msg_body: dict[str, Any] | None = None) -> None:
        """Send command to API."""

        msg_body = msg_body or {}

        if not self.get(id):
            raise UnknownDevice(f"Device {id} not found.")

        await self._bridge.post(
            path=self._resource_url_override or self.resource_type,
            action=action,
            id=id,
            json={"statePollOnly": False, **msg_body},
        )

    async def _refresh(self, pre_fetched: list[Resource] | None = None, resource_id: str | None = None) -> None:
        """
        Initialize controllers using API response data, either fetched here or by another controller.

        Request all devices in the controller's universe (either all available or all specified by target_device_ids):

            pre_fetched = None
            resource_id = None

            Any missing resources previously registered by this controller will be unregistered.

        Request a single device:

            pre_fetched = None
            resource_id = <device_id>

            If the device is not found, it will be unregistered. Other devices will be left alone.

        Use resources retrieved by another controller:

            pre_fetched = <list of resources>
            resource_id = None

            Any missing resources previously registered by this controller will be unregistered.
        """

        log.info("[%s] Refreshing controller...", self.resource_type.name)

        if pre_fetched and resource_id:
            raise NotImplementedError

        if (self._api_data_provider and not pre_fetched) or (
            self._requires_target_ids and not self._target_device_ids
        ):
            return

        if not pre_fetched:
            ids: str | set[str] | None = None

            # Requests for single devices must use the single device format (/devices/locks/12345-098), not the multi-device format (/devices/locks?id[]=12345-098).
            if resource_id or len(self._target_device_ids) == 1:
                ids = resource_id or self._target_device_ids.pop()
            elif self._target_device_ids:
                ids = self._target_device_ids
            else:
                ids = None

            response = await self._bridge.get(self._resource_url_override or self.resource_type, ids)

            response.data = self._device_filter(response.data)

            # Update included resources cache. If this is a full refresh, overwrite existing cache.
            if resource_id:
                self._included_resources.append(*(response.included or []))
            else:
                self._included_resources = response.included or []

            # Send included resources to downstream controllers.
            for resource_type, callbacks in self._api_data_receivers.items():
                included_resources = [
                    included_resource
                    for included_resource in self._included_resources
                    if included_resource.type == resource_type
                ]
                if included_resources:
                    for callback in callbacks:
                        if iscoroutinefunction(callback):
                            task = asyncio.create_task(callback(included_resources))
                            self._background_tasks.add(task)
                            task.add_done_callback(self._background_tasks.discard)
                        else:
                            callback(included_resources)

            # Return normalized response data for current resource type.
            pre_fetched = [*(response.data if isinstance(response.data, list) else [response.data])]

        # Find and instantiate supported devices.
        discovered_resource_ids = set({})
        for resource in pre_fetched:
            if (
                resource.type == self.resource_type
                and await self._register_or_update_resource(resource) is not None
            ):
                discovered_resource_ids.update({resource.id})

        # Unregister devices that failed to be instantiated or (in the case of multi-device endpoints) appeared in a previous API response but not the current one.
        if resource_id:
            # If we retrieved data for a specific device
            if resource_id not in discovered_resource_ids:
                await self._unregister_resource(resource_id)
        else:
            for missing_resource_id in self._resources.keys() - discovered_resource_ids:
                await self._unregister_resource(missing_resource_id)

    #############################
    # WEBSOCKET UPDATE HANDLERS #
    #############################

    async def _base_handle_event(self, message: EventBrokerMessage) -> None:
        """Universal event handling for WebSockets messages."""

        if not isinstance(message, RawResourceEventMessage):
            return

        try:
            adc_resource = self[message.ws_message.device_id]
        except KeyError:
            return

        # Handle state updates for all controllers that have a state map.
        if (
            self._event_state_map
            and isinstance(message.ws_message, EventWSMessage)
            and message.ws_message.subtype in self._event_state_map
        ):
            adc_resource.api_resource.attributes.update(
                {
                    ATTR_STATE: self._event_state_map[message.ws_message.subtype].value,
                    ATTR_DESIRED_STATE: self._event_state_map[message.ws_message.subtype].value,
                }
            )

        # Send to individual controller for additional changes.
        with contextlib.suppress(NotImplementedError):
            adc_resource = await self._handle_event(adc_resource, message.ws_message)

        # Update registry and send notification to subscribers.
        await self._register_or_update_resource(adc_resource.api_resource)

    async def _handle_event(self, adc_resource: AdcResourceT, message: BaseWSMessage) -> AdcResourceT:
        """
        Individual controller functions for handling WebSockets messages.

        Takes api_resource and WebSocket message as input. Returns updated api_resource.
        """

        raise NotImplementedError

    ###############################
    # SUB-CONTROLLER REGISTRATION #
    ###############################

    async def subcontroller_data_subscribe(
        self, resource_types: list[ResourceType], callback: Callable[[list[Resource]], Awaitable | None]
    ) -> Callable:
        """Register controller that depends on this controller for API updates."""

        for resource_type in resource_types:
            self._api_data_receivers.setdefault(resource_type, []).append(callback)

        # log.debug(f"New API data subscriber for {resource_types} to {self.resource_type.name} controller.")

        # Send data if dependent subscribes after fetch.
        if len(self._included_resources) > 0:
            for resource_type in resource_types:
                resources = [
                    included_resource
                    for included_resource in self._included_resources
                    if included_resource.type == resource_type
                ]
                if iscoroutinefunction(callback):
                    task = asyncio.create_task(callback(resources))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
                else:
                    callback(resources)

        def unsubscribe() -> None:
            """Unregister dependent controller."""
            for resource_type in resource_types:
                self._api_data_receivers[resource_type].remove(callback)

        return unsubscribe

    ##################
    # DEVICE RECORDS #
    ##################

    async def _register_or_update_resource(self, resource: Resource) -> str | None:
        """Instantiate resource, add to controller's registry, and notify subscribers."""

        new_adc_resource = self._resource_class(resource)

        # Check whether any underlying data has changed. We instantiate first (above) since we only
        # want to notify subscribers if attributes used by this library have changed.
        if ((existing_adc_resource := self.get(resource.id)) is not None) and (
            existing_adc_resource.attributes == new_adc_resource.attributes
        ):
            return resource.id

        try:
            self._resources.update({resource.id: new_adc_resource})
        except Exception:
            log.exception(
                "[%s] Failed to instantiate %s, %s. Moving on...",
                self.resource_type.name,
                resource.type,
                resource.id,
            )
            return None

        if existing_adc_resource:
            log.debug(
                "[%s] Updated %s %s.",
                self.resource_type.name,
                resource.id,
                getattr(new_adc_resource.attributes, "description", ""),
            )
            self._bridge.events.publish(
                ResourceEventMessage(
                    topic=EventBrokerTopic.RESOURCE_UPDATED, id=resource.id, resource=new_adc_resource
                )
            )
        else:
            log.debug(
                "[%s] Registered %s %s.",
                self.resource_type.name,
                resource.id,
                getattr(new_adc_resource.attributes, "description", ""),
            )
            self._bridge.events.publish(
                ResourceEventMessage(
                    topic=EventBrokerTopic.RESOURCE_ADDED, id=resource.id, resource=new_adc_resource
                )
            )

        return resource.id

    async def _unregister_resource(self, resource_id: str) -> None:
        """Remove resource from registry and notify subscribers."""

        log.debug("[%s] Unregistering %s...", self.resource_type.name, resource_id)

        resource = self._resources.pop(resource_id, None)

        self._bridge.events.publish(
            ResourceEventMessage(topic=EventBrokerTopic.RESOURCE_DELETED, id=resource_id, resource=resource)
        )

    ####################
    # OBJECT FUNCTIONS #
    ####################

    def get(self, id: str, default: Any = None) -> AdcResourceT | Any | None:
        """Return resource by ID."""
        return self._resources.get(id, default)

    def __getitem__(self, id: str) -> AdcResourceT:
        """Return resource by ID."""
        return self._resources[id]

    def __iter__(self) -> Iterator[AdcResourceT]:
        """Iterate over resources."""
        return iter(self._resources.values())

    def __contains__(self, id: str) -> bool:
        """Return whether resource is present."""
        return id in self._resources

    @property
    def resources_pretty(self) -> Group:
        """Return pretty Rich representation of resources in controller."""

        return resources_pretty(self.resource_type.name, list(self._resources.values()))

    @property
    def resources_raw(self) -> Group:
        """Return Rich representation raw JSON for all controller resources."""

        return resources_raw(self.resource_type.name, list(self._resources.values()))

    @property
    def included_raw_str(self) -> Group:
        """Return Rich representation of raw JSON for all controller resources."""

        return resources_raw(f"{self.resource_type.name} Children", list(self._included_resources))
