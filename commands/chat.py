from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Union

import discord

from commands import chat_tools
from commands.base import BaseCommand
from utils.messages import send_long_message
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
                'content': "The assistant should be informative.",
            },
        ]

    def has_message(self, message_id: int) -> bool:
        return message_id in self.discord_messages

    def add_user_message(self, message: discord.Message, image_urls: list[str]) -> None:
        # Get the user's prompt
        prompt = message.clean_content.strip()
        if prompt.startswith(self.bot_mention):
            # Remove the bot mention if there is one
            prompt = prompt[len(self.bot_mention) :].strip()

        content = [{'type': 'text', 'text': prompt}]
        for image_url in image_urls:
            content.append({'type': 'image_url', 'image_url': image_url})

        self.openai_messages.append({'role': 'user', 'content': content})

    def add_assistant_messages(self, messages: list[discord.Message]) -> None:
        for message in messages:
            self.discord_messages.add(message.id)
            self.openai_messages.append({'role': 'assistant', 'content': message.clean_content})

    def add_tool_messages(self, messages: list[discord.Message]) -> None:
        for message in messages:
            self.discord_messages.add(message.id)

    @property
    def bot_mention(self) -> str:
        return f'@{self._client.user.name}'

    def __hash__(self) -> int:
        return self._id


class ChatCommand(BaseCommand):
    command = ''
    conversations: set[ChatConversation] = set()
    allow_pm = True

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
        is_dm = isinstance(response_channel, discord.DMChannel)
        if is_dm:
            await response_channel.typing()
        else:
            loading = await response_channel.send('<a:loading:1085904578798694410>')

        image_urls = self.extract_image_attachments(message)[:5]

        # Get or create Conversation
        conversation = self.get_or_create_conversation(message)
        conversation.add_user_message(message, image_urls)

        # Get response from the API
        error_message = None
        try:
            response_text, tool_calls = await openai_chat(
                conversation.openai_messages,
                tools=None,
                user=message.author.name,
            )
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

        # Handle tool calls
        if tool_calls:
            responses = await self.handle_tool_calls(message, response_channel, tool_calls)
            conversation.add_tool_messages(responses)
            return responses[0]

        # Send response
        if not is_dm:
            await response_channel.delete_messages([loading])
        responses = await send_long_message(response_channel, response_text, reference=message)
        conversation.add_assistant_messages(responses)

        return responses[0]

    @staticmethod
    def extract_image_attachments(message: discord.Message) -> list[str]:
        image_urls = []
        for attachment in message.attachments:
            if attachment.content_type.startswith('image'):
                image_urls.append(attachment.url)
        return image_urls

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

    async def handle_tool_calls(
        self,
        message: discord.Message,
        response_channel: discord.TextChannel,
        tool_calls: list[dict],
    ) -> list[discord.Message]:
        for tool_call in tool_calls:
            function_name = tool_call['function']['name']
            function_args = json.loads(tool_call['function']['arguments'])

            if function_name == 'generate_images':
                images = await chat_tools.generate_images(
                    self.client, function_args['prompts'], function_args['size']
                )
                response = await response_channel.send(
                    files=[discord.File(image, filename='image.png') for image in images],
                    reference=message,
                )
                return [response]
