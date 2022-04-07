import re
from typing import Optional

import discord

import config
from commands.base import BaseCommand
from components.confimation import ConfirmationMessage
from components.progress_bar import ProgressBarMessage


class DeleteEvents(BaseCommand):
    command = '!events delete'
    channels = {config.DISCORD_ADMIN_CHANNEL_ID}

    async def handle(
        self, message: discord.Message, response_channel: discord.TextChannel
    ) -> Optional[discord.Message]:
        # Get regex
        regex = message.content[len(self.command) :].strip()
        if not regex:
            return await response_channel.send(content=f'Wrong arguments. `{self.command} <regex>`')
        regex = re.compile(regex)

        # Filter events that match the regex
        all_events = message.guild.scheduled_events
        events_to_delete = []
        for event in all_events:
            if regex.match(event.name):
                events_to_delete.append(event)

        if not events_to_delete:
            return await response_channel.send('No events matched')

        # Ask for confirmation
        confirmation_text = '\n'.join(event.name for event in events_to_delete)
        confirmation_text = (
            f'Matched {len(events_to_delete)} events:\n\n'
            f'{confirmation_text}\n\n'
            f'Do you want to delete these events?'
        )
        confirmation = ConfirmationMessage(
            self.client, response_channel, message.author, confirmation_text
        )
        if not await confirmation.ask():
            return None

        # Create progress bar
        progress_bar = ProgressBarMessage(
            self.client,
            response_channel,
            f'Deleting {len(events_to_delete)} events\n'
            '`[{progress_bar}] {percentage:3.0f}% {comment}`',
        )
        await progress_bar.send(comment=f'0/{len(events_to_delete)}')

        # Delete events
        deleted_count = 0
        for event in events_to_delete:
            await event.delete(reason=f'Deleted by {message.author}: {message.content}')
            deleted_count += 1
            await progress_bar.update(
                deleted_count,
                len(events_to_delete),
                comment=f'{deleted_count}/{len(events_to_delete)}',
            )

        # Delete progress bar
        await progress_bar.delete()

        return await response_channel.send(content='Finished')
