"""Base controller for Ember.js/JSON:API based components."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import ABC
from asyncio import Task, iscoroutinefunction
from collections.abc import Awaitable, Callable, Iterator
from enum import IntEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Generic

from pyalarmdotcomajax.const import ATTR_DESIRED_STATE, ATTR_STATE, URL_BASE
from pyalarmdotcomajax.controllers import AdcResourceT, EventCallBackType, EventType
from pyalarmdotcomajax.exceptions import UnknownDevice
from pyalarmdotcomajax.models.base import ResourceType
from pyalarmdotcomajax.models.jsonapi import (
    JsonApiSuccessResponse,
    Resource,
)
from pyalarmdotcomajax.websocket.client import SupportedResourceEvents
from pyalarmdotcomajax.websocket.messages import BaseWSMessage, EventWSMessage, ResourceEventType

if TYPE_CHECKING:
    from pyalarmdotcomajax import AlarmBridge

log = logging.getLogger(__name__)


class BaseController(ABC, Generic[AdcResourceT]):
    """Base controller for Ember.js/JSON:API based components."""

    # ResourceTypes to be pulled from API response data object.
    _resource_type: ClassVar[ResourceType]
    # AdcResource class to be created by this controller.
    _resource_class: type[AdcResourceT]
    # URL to be used for API requests.
    _resource_url: ClassVar[str | None]
    # Restricts this controller to specific device IDs.
    _requires_target_ids: ClassVar[bool] = False
    # WebSocket events supported by this controller.
    _supported_resource_events: ClassVar[SupportedResourceEvents | None] = None
    # Maps websocket events to states.
    _event_state_map: ClassVar[MappingProxyType[ResourceEventType, IntEnum] | None] = None

    def __init__(
        self,
        bridge: AlarmBridge,
        data_provider: BaseController | None = None,
        target_device_ids: list[str] | None = None,
    ) -> None:
        """Initialize base controller."""

        # Tracks whether the controller has been initialized.
        self._initialized: bool = False

        self._bridge = bridge

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

        # Tracks event subscribers.
        self.subscribers: list[EventCallBackType] = []

        # Holds references to asyncio tasks to prevent them from being garbage collected before completion.
        self._background_tasks: set[Task] = set()

        if target_device_ids:
            self._target_device_ids.add(*target_device_ids)

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
            self._bridge.ws_controller.subscribe_resource(self._base_handle_event, self._supported_resource_events)

        # Bail now if we depend on another controller for API data.
        if self._api_data_provider:
            self._initialized = True
            self._api_data_unsubscribe = await self._api_data_provider.subcontroller_data_subscribe(
                [self._resource_type], self._refresh
            )
            return

        if target_device_ids:
            self._target_device_ids.add(*target_device_ids)

        await self._refresh()

    async def add_target(self, resource_id: str) -> AdcResourceT | None:
        """Add a device ID to the controller's list of targets."""

        await self._refresh(resource_id=resource_id)

        return self._resources.get(resource_id)

    async def _post_init(self) -> None:
        """Post-initialization steps. To be overridden by subclasses."""

        pass

    #####################
    # DEVICE MANAGEMENT #
    #####################

    def _device_filter(self, response: JsonApiSuccessResponse) -> JsonApiSuccessResponse:
        """
        Filter out unsupported devices from API response.

        Intended to be overridden by child classes.
        """

        return response

    async def _send_command(self, id: str, command: str, msg_body: dict[str, Any] | None = None) -> None:
        """Send command to API."""

        msg_body = msg_body or {}

        if not self._resource_url:
            raise NotImplementedError

        if not self.get(id):
            raise UnknownDevice(f"Device {id} not found.")

        await self._bridge.post(
            url=f"{self._resource_url.format(URL_BASE, id)}/{command}",
            json={"statePollOnly": False, **msg_body},
        )

    async def _refresh(self, resources: list[Resource] | None = None, resource_id: str | None = None) -> None:
        """
        Update controller using API response data. If API data is not provided, fetch from API.

        Assumes that resources list always contains complete universe of devices discoverable by this endpoint.

        This function is used:
            1. To initialize controllers that retrieve resources from multi-resource (non-single-serve) endpoints.
            2. By parent controllers to update dependent controllers with pre-fetched data.
            3. By single-serve controllerst that can only fetch data for one resource instance at a time.
        """

        log.info(f"[{self._resource_type.name}] Refreshing controller...")

        if (self._api_data_provider and not resources) or (
            self._requires_target_ids and not self._target_device_ids
        ):
            return

        if not resources:
            if not self._resource_url:
                raise NotImplementedError

            request_urls = []
            if resource_id:
                request_urls.append(self._resource_url.format(URL_BASE, resource_id))
            elif self._target_device_ids:
                request_urls.append(
                    *[self._resource_url.format(URL_BASE, device_id) for device_id in self._target_device_ids]
                )
            else:
                request_urls.append(self._resource_url.format(URL_BASE, ""))

            resources = []

            for request_url in request_urls:
                response = await self._bridge.get(url=request_url)

                response = self._device_filter(response)

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
                        if included_resource.type_ == resource_type
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
                resources.append(*(response.data if isinstance(response.data, list) else [response.data]))

        # Find and instantiate supported devices.
        discovered_resource_ids = set({})
        for resource in resources:
            if (
                resource.type_ == self._resource_type
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

        await self._post_init()

    #############################
    # WEBSOCKET UPDATE HANDLERS #
    #############################

    async def _base_handle_event(self, message: BaseWSMessage) -> None:
        """Universal event handling for WebSockets messages."""

        try:
            adc_resource = self[message.device_id]
        except KeyError:
            log.warning(
                f"[{self._resource_type.name}] Received state change for unknown {self._resource_type.name} {message.device_id}."
            )
            return

        # Handle state updates for all controllers that have a state map.
        if (
            self._event_state_map
            and isinstance(message, EventWSMessage)
            and message.subtype in self._event_state_map
        ):
            adc_resource.api_resource.attributes.update(
                {
                    ATTR_STATE: self._event_state_map[message.subtype].value,
                    ATTR_DESIRED_STATE: self._event_state_map[message.subtype].value,
                }
            )

        # Send to individual controller for additional changes.
        with contextlib.suppress(NotImplementedError):
            adc_resource = await self._handle_event(adc_resource, message)

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

        # log.debug(f"New API data subscriber for {resource_types} to {self._resource_type.name} controller.")

        # Send data if dependent subscribes after fetch.
        if len(self._included_resources) > 0:
            for resource_type in resource_types:
                resources = [
                    included_resource
                    for included_resource in self._included_resources
                    if included_resource.type_ == resource_type
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

    ######################
    # EVENT TRANSMISSION #
    ######################

    def event_subscribe(self, callback: EventCallBackType) -> Callable:
        """
        Subscribe to events.

        Subscribes bridge to events from this controller. Returns an unsubscribe function.
        """

        self.subscribers.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe from events."""
            self.subscribers.remove(callback)

        return unsubscribe

    async def _send_event(
        self, event_type: EventType, resource_id: str, resource: AdcResourceT | None = None
    ) -> None:
        """Send event to subscribers."""

        for subscriber in self.subscribers:
            if iscoroutinefunction(subscriber):
                task = asyncio.create_task(subscriber(event_type, resource_id, resource))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            else:
                subscriber(event_type, resource_id, resource)

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
                f"[{self._resource_type.name}] Failed to instantiate {resource.type_} {resource.id}. Moving on..."
            )
            return None

        if existing_adc_resource:
            log.debug(
                f"[{self._resource_type.name}] Updated {resource.id} {getattr(new_adc_resource.attributes, 'description', '')}."
            )
            await self._send_event(EventType.RESOURCE_UPDATED, resource.id, new_adc_resource)
        else:
            log.debug(
                f"[{self._resource_type.name}] Registered {resource.id} {getattr(new_adc_resource.attributes, 'description', '')}."
            )
            await self._send_event(EventType.RESOURCE_ADDED, resource.id, new_adc_resource)

        return resource.id

    async def _unregister_resource(self, resource_id: str) -> None:
        """Remove resource from registry and notify subscribers."""

        log.debug(f"[{self._resource_type.name}] Unregistering {resource_id}...")

        resource = self._resources.pop(resource_id, None)

        await self._send_event(EventType.RESOURCE_DELETED, resource_id, resource)

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
