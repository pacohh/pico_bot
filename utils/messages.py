from typing import Optional

import discord

import utils.lists
from utils import emojis

MESSAGE_MAX_LENGTH = 1900


async def send_long_message(
    channel: discord.abc.Messageable,
    content: str,
    reference: Optional[discord.message.Message] = None,
) -> list[discord.message.Message]:
    messages = []

    lines = _split_lines(content)
    sub_lines = []
    sub_len = 0
    first_message = True
    for line in lines:
        if sub_len + len(line) > MESSAGE_MAX_LENGTH:
            message = await _send_lines(
                channel,
                sub_lines,
                reference=reference if first_message else None,
            )
            messages.append(message)
            sub_lines = []
            sub_len = 0
            first_message = False

        sub_lines.append(line)
        sub_len += len(line)

    if sub_lines:
        message = await _send_lines(
            channel,
            sub_lines,
            reference=reference if first_message else None,
        )
        messages.append(message)

    return messages


def _split_lines(content: str) -> list[str]:
    lines = []
    for line in content.split('\n'):
        if len(line) > MESSAGE_MAX_LENGTH:
            chunks = utils.lists.chunks(line, MESSAGE_MAX_LENGTH - 4)
            chunks[0] = f'{chunks[0]} …'
            chunks[-1] = f'… {chunks[-1]}'
            for idx in range(1, len(chunks) - 1):
                chunks[idx] = f'… {chunks[idx]} …'
            lines.extend(chunks)
        else:
            lines.append(line)
    return lines


async def _send_lines(
    channel: discord.abc.Messageable,
    lines: list[str],
    reference: Optional[discord.message.Message] = None,
) -> discord.message.Message:
    content = '\n'.join(lines)
    if content.startswith('\n'):
        content = emojis.BLANK + content
    if content.endswith('\n'):
        content = content + emojis.BLANK
    return await channel.send(content, reference=reference)
