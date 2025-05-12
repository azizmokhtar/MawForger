from typing import Callable, Dict, List
from collections import defaultdict

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def publish(self, event_type: str, data=None):
        for handler in self._handlers.get(event_type, []):
            try:
                await handler(data)
            except Exception as e:
                print(f"Error handling event {event_type}: {e}")