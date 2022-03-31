import logging

import discord
from discord import RawReactionActionEvent

import background_tasks
import commands
import config

COMMANDS = []
REACTION_HANDLERS = []

logger = logging.getLogger(__name__)
client = discord.Client()


def main():
    config.setup_logging()
    register_commands()
    register_reaction_handlers()
    register_background_tasks()
    client.run(config.DISCORD_TOKEN)


def register_commands():
    """Register all available commands."""
    register_command(commands.WhoCommand)


def register_command(command_class):
    """Register a command class."""
    command = command_class(client)
    COMMANDS.append(command)


def register_reaction_handlers():
    """Register all available reaction handlers."""
    register_reaction_handler(commands.WhoRefreshReactionHandler)


def register_reaction_handler(handler_class):
    """Register a reaction handler class."""
    command = handler_class(client)
    REACTION_HANDLERS.append(command)


def register_background_tasks():
    """Register all background tasks."""
    client.loop.create_task(background_tasks.BattlemetricsPlayersTask(client).start())


@client.event
async def on_ready():
    logger.info('Logged in as "%s" (%s)', client.user.name, client.user.id)


@client.event
async def on_message(message):
    for command in COMMANDS:
        if await command.should_handle(message):
            log_message(message)
            await command.handle_message(message)
            return


@client.event
async def on_reaction_add(reaction, user):
    for handler in REACTION_HANDLERS:
        if await handler.should_handle(reaction, user):
            log_reaction(reaction, user)
            await handler.handle_message(reaction, user)
            return


@client.event
async def on_raw_reaction_add(event: RawReactionActionEvent):
    """
    Handle MESSAGE_REACTION_ADD events for messages that are not in the client's
    cache.

    Discordpy's client only handles message events when the messages are in the
    client's cache. For a message to be in in the client's cache it has to be
    created while the bot is running, which isn't always the case for some
    messages for which we want to handle events.

    To circumvent this we handle the raw MESSAGE_REACTION_ADD events, getting
    all the necessary information, and caching the message so that future
    reactions can be directly handled by the client.
    """

    # We only want to handle events on messages that aren't cached by the
    # client, as the client won't handle them automatically.
    cached_messages_ids = (message.id for message in client.cached_messages)
    if event.message_id in cached_messages_ids:
        return

    # Don't handle PMs
    if not event.guild_id:
        return

    # Get guild
    guild = client.get_guild(event.guild_id)
    if not guild:
        return

    # Get message and cache it
    channel = client.get_channel(event.channel_id)
    message = await channel.fetch_message(event.message_id)
    client._connection._messages.append(message)

    # Get reaction and member objects, and handle the reaction
    data = {'me': event.user_id == client.user.id}
    reaction = discord.Reaction(message=message, emoji=event.emoji, data=data)
    member = guild.get_member(event.user_id)

    await on_reaction_add(reaction, member)


def log_message(message):
    guild = f'Guild: {message.guild.id}:"{message.guild.name}" | ' if message.guild else ''
    logger.info(
        'Handling message | %sChannel: %s:"%s" | Author: "%s" | Message: "%s"',
        guild,
        message.channel.id,
        message.channel.name or '',
        message.author,
        message.clean_content,
    )


def log_reaction(reaction, user):
    message = reaction.message
    guild = f'Guild: {message.guild.id}:"{message.guild.name}" | ' if message.guild else ''
    logger.info(
        'Handling reaction | %sChannel: %s:"%s" | Author: "%s" | Message: "%s" | '
        'User: %s | Emote: %s',
        guild,
        message.channel.id,
        message.channel.name or '',
        message.author,
        message.clean_content,
        user,
        reaction.emoji,
    )


if __name__ == '__main__':
    main()
