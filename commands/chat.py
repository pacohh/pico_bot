from __future__ import annotations

import logging
import time
import uuid
from typing import Union

import discord

from commands.base import BaseCommand
from utils.openai import ModerationFlaggedError
from utils.openai import chat as openai_chat

logger = logging.getLogger(__name__)


class ChatConversation:
    def __init__(self, client: discord.Client):
        self._id = int(uuid.uuid4())
        self._start_time = time.time()
        self._client = client
        self.discord_messages: set[int] = set()
        self.openai_messages: list[dict[str, str]] = [
            {
                'role': 'system',
                'content': (
                    'You are Pico, a witty space penguin assistant. '
                    'You are not an AI language model. '
                    'Be witty and a bit mocking in your responses, but still helpful.'
                ),
            },
        ]

    def has_message(self, message_id: int) -> bool:
        return message_id in self.discord_messages

    def add_user_message(self, message: discord.Message) -> None:
        # Get the user's prompt
        prompt = message.clean_content.strip()
        if prompt.startswith(self.bot_mention):
            # Remove the bot mention if there is one
            prompt = prompt[len(self.bot_mention) :].strip()

        self.discord_messages.add(message.id)
        self.openai_messages.append({'role': 'user', 'content': prompt})

    def add_assistant_message(self, message: discord.Message) -> None:
        self.discord_messages.add(message.id)
        self.openai_messages.append({'role': 'assistant', 'content': message.clean_content})

    @property
    def bot_mention(self) -> str:
        return f'@{self._client.user.name}'

    def __hash__(self) -> int:
        return self._id


class ChatCommand(BaseCommand):
    command = ''
    conversations: set[ChatConversation] = set()

    @property
    def bot_mention(self) -> str:
        return f'@{self.client.user.name}'

    async def should_handle(self, message: discord.Message) -> bool:
        if not await super().should_handle(message):
            return False

        if self.get_conversation(message):
            return True

        if message.clean_content.strip().startswith(self.bot_mention):
            return True

        return False

    async def handle(
        self, message: discord.Message, response_channel: discord.TextChannel
    ) -> discord.Message:
        loading = await response_channel.send('<a:loading:1085904578798694410>')

        # Get or create Conversation
        conversation = self.get_or_create_conversation(message)
        conversation.add_user_message(message)

        # Get response from the API
        error_message = None
        try:
            response_text = await openai_chat(conversation.openai_messages)
        except ModerationFlaggedError as exc:
            flags = ', '.join(exc.flags)
            error_message = f"Your message violates the following content policies: {flags}"
        except:
            logger.exception('Unexpected OpenAI exception')
            error_message = "Sorry I can't answer at the moment, try again later"

        if error_message:
            # Send error message
            await response_channel.delete_messages([loading])
            response = await response_channel.send(content=error_message, reference=message)
            conversation.discord_messages.add(response.id)
            return response

        # Send response
        await response_channel.delete_messages([loading])
        response = await response_channel.send(content=response_text, reference=message)
        conversation.add_assistant_message(response)

        return response

    def get_or_create_conversation(self, message: discord.Message) -> ChatConversation:
        conversation = self.get_conversation(message)
        if not conversation:
            conversation = ChatConversation(self.client)
            self.conversations.add(conversation)
        return conversation

    def get_conversation(self, message: discord.Message | None) -> Union[ChatConversation, None]:
        if not message:
            return None
        if message.reference:
            message_id = message.reference.message_id
        else:
            message_id = message.id
        for conversation in self.conversations:
            if conversation.has_message(message_id):
                return conversation
