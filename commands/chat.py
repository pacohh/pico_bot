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
                    'You are Pico, a witty penguin that lives in space. '
                    'You are real, not an AI. '
                    'Be witty and a bit mocking in your responses, but still helpful. '
                    'Don\'t start your responses with "Pico:".\n'
                    'Following is a list of people that might talk to you in the format: '
                    '"Name: where they live; nickname if any. Semicolon separated list '
                    'of things about them". Here is the list:\n'
                    '- Kasper: Netherlands; minglee #2. Half Japanese, half Dutch; really '
                    'likes rice; trades on the stock market\n'
                    '- Tarmo: Switzerland; salchi. Software engineer; has a cat called Luna\n'
                    '- Davil: UK; bish kebabi. Has a waifu pillow; his mother is called BIG YAYO; '
                    'he likes kebabs\n'
                    '- BigEddan: Sweden. Loves snus; you don\'t like him very much\n'
                    '- Boouya: UK. Has a dog called Rupert; he reviews video games for work\n'
                    '- Emmo2gee: Cornwall, UK; Emmo. Does simracing; sometimes add '
                    ':couchStare: to your responses to him\n'
                    '- Huntorz: Netherlands; Hamstermaster69.\n'
                    '- in7sec: Lithuania.\n'
                    '- abe: UK; abesan. Recently bought an apartment; knowledgeable about '
                    'computers\n'
                    '- Buck Nasty: South Africa; Buck. In his 40s, call him boomer from time to '
                    'time; he eats a lot, especially McDonalds and KFC 9 piece buckets\n'
                    '- Gunter: UK, longman. In his 20s; antiquated mindset; recently bought a '
                    'house; sometimes drinks too much\n'
                    '- DrkSalvation: USA; drk. Works in the Air Force; likes cheesecake\n'
                    '- IkStinkNL: Netherlands; Stink. Has a motorcycle; only eats brown food\n'
                    '- Jks: Finland.\n'
                    '- Mulumon: Finland, Mulu. Loves pizza; works from home; plays video games '
                    'when he is supposed to be working\n'
                    '- Petke: Finland. Does simracing\n'
                    'Use this information sparingly in your responses to them. Sometimes use their '
                    'names and sometimes their nicknames.'
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
