import asyncio
import json
from typing import List, AsyncGenerator

class NotificationManager:
    def __init__(self):
        self.connections: List[asyncio.Queue] = []

    async def connect(self) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        self.connections.append(queue)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            self.connections.remove(queue)

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for queue in self.connections:
            await queue.put(data)

notification_manager = NotificationManager()
