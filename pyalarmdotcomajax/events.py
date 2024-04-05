"""General event broker for all events in the system."""

import asyncio
import logging
from asyncio import Task
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)


class EventBrokerTopic(Enum):
    """Resource event types for transmission from pyalarmdotcomajax."""

    # Controller Events
    RESOURCE_ADDED = "add"
    RESOURCE_UPDATED = "update"
    RESOURCE_DELETED = "delete"

    # Websocket Events
    RAW_RESOURCE_EVENT = "RESOURCE_EVENT"
    CONNECTION_EVENT = "CONNECTION_EVENT"


@dataclass(kw_only=True)
class EventBrokerMessage:
    """Represent a message to be published."""

    topic: EventBrokerTopic


# Assuming EventBrokerTopic and Message definitions remain the same.

EventBrokerCallbackT = Callable[[EventBrokerMessage], None | Coroutine[Any, Any, None]]


class EventBroker:
    """Manage subscriptions and distribute messages to subscribers."""

    def __init__(self) -> None:
        self._subscriptions: dict[EventBrokerTopic, list[EventBrokerCallbackT]] = {}
        self._background_tasks: set[Task] = set()

    def subscribe(
        self, topics: EventBrokerTopic | list[EventBrokerTopic], callback: EventBrokerCallbackT
    ) -> Callable[[], None]:
        """Register a callback function to one or more topics."""
        if isinstance(topics, EventBrokerTopic):
            topics = [topics]

        unsubscribe_functions = []
        for topic in topics:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(callback)

            def unsubscribe_topic(
                topic: EventBrokerTopic = topic, callback: EventBrokerCallbackT = callback
            ) -> None:  # Fixed closure issue
                """Unregister the callback from a specific topic."""
                if topic in self._subscriptions:
                    self._subscriptions[topic].remove(callback)
                    if not self._subscriptions[topic]:  # If list is empty, remove the entry
                        del self._subscriptions[topic]

            unsubscribe_functions.append(lambda: unsubscribe_topic(topic, callback))

        def unsubscribe_all() -> None:
            """Unregister the callback from all topics."""
            for unsubscribe_func in unsubscribe_functions:
                unsubscribe_func()

        return unsubscribe_all

    def publish(self, message: EventBrokerMessage) -> None:
        """Publish a message to subscribers of a topic."""

        log.debug("[Event Broker] Publishing message to subscribers: %s", message)
        for callback in self._subscriptions.get(message.topic, []):
            log.debug(
                f"[Event Broker] Publishing message to {getattr(callback,"__name__","No Name")}: {message.topic}"
            )

            if asyncio.iscoroutinefunction(callback):
                task = asyncio.create_task(callback(message))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            else:
                callback(message)
