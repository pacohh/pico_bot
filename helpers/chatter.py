from __future__ import annotations

import asyncio

import openai
import openai.types.beta
from openai.types.beta.threads import ThreadMessage


class Chatter:
    def __init__(
        self,
        client: openai.AsyncClient,
        assistant_id: str,
        thread_id: str,
    ) -> None:
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id

    async def add_message(self, content: str) -> ThreadMessage:
        message = await self._client.beta.threads.messages.create(
            thread_id=self._thread_id,
            role='user',
            content=content,
        )
        return message

    async def run(self) -> list[ThreadMessage]:
        # Create run
        run = await self._client.beta.threads.runs.create(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
        )

        # Wait for the run to complete
        while True:
            run = await self._client.beta.threads.runs.retrieve(
                thread_id=self._thread_id,
                run_id=run.id,
            )
            if run.status in ['queued', 'in_progress']:
                # The run hasn't finished
                await asyncio.sleep(1)
                continue
            if run.status != 'completed':
                # The run didn't succeed
                return []
            # The run succeeded
            break

        # Return run messages
        messages = await self._client.beta.threads.messages.list(
            thread_id=self._thread_id,
            limit=50,
        )
        messages = [message for message in messages.data if message.run_id == run.id]
        return messages
