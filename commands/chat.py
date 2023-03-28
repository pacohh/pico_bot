from __future__ import annotations

import logging
import time
import uuid
from copy import deepcopy
from typing import Union

import discord

from commands.base import BaseCommand
from utils import emojis
from utils.openai import ModerationFlaggedError
from utils.openai import chat as openai_chat

WEIRD_MESSAGES = [
    {
        'role': 'system',
        'content': (
            "You are a sentiment analysis bot. "
            "Given a user message you will analyze it and you'll decide how weird "
            "it is on a scale from 0 to 10, 10 being the most weird. "
            "You will only answer with a number between 0 and 10."
        ),
    },
    # Example
    {
        'role': 'user',
        'content': "@abe they've changed the layout of spotify again :PU_PepeCringeZoom:",
    },
    {'role': 'assistant', 'content': "4"},
    # Example
    {'role': 'user', 'content': "it kinda does and doesn't idk"},
    {'role': 'assistant', 'content': "1"},
    # Example
    {'role': 'user', 'content': "is the weather good enough for a stroll?"},
    {'role': 'assistant', 'content': "0"},
    # Example
    {'role': 'user', 'content': "hotties :wankege:"},
    {'role': 'assistant', 'content': "8"},
    # Example
    {'role': 'user', 'content': "jizz in a pot?"},
    {'role': 'assistant', 'content': "10"},
]


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
                    "You are the world's leading expert in whatever I am about to ask you about"
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

        prompt = f'{message.author.display_name}: {prompt}'

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


class WeirdReaction(BaseCommand):
    command = ''
    ignored_prefixes = {'<:', 'http:', 'https://'}

    async def should_handle(self, message):
        if not await super().should_handle(message):
            return False

        msg = message.content.lower()
        for prefix in self.ignored_prefixes:
            if msg.startswith(prefix):
                return False

        return True

    async def handle(self, message: discord.Message, response_channel: discord.TextChannel) -> None:
        msg = message.clean_content.strip()
        if len(msg) > 200:
            return

        is_weird = await self.is_weird(msg, message.author.name)
        if is_weird:
            await message.add_reaction(emojis.COUCH_STARE)

    @staticmethod
    async def is_weird(message: str, user: str) -> bool:
        messages = deepcopy(WEIRD_MESSAGES)
        messages.append({'role': 'user', 'content': message})

        try:
            response = await openai_chat(messages)
        except ModerationFlaggedError:
            return True

        try:
            score = int(response.strip())
            is_weird = score >= 7
            logger.info('Weirdness score %d, weird = %s | %s: %s', score, is_weird, user, message)
            return is_weird
        except:
            return False
