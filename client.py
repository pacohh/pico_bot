from __future__ import annotations

from typing import Any

import discord
import openai
from discord import Intents

import background_tasks
import commands
import config
from commands.base import BaseCommand
from helpers.chatter import Chatter

COMMANDS = []
REACTION_HANDLERS = []


class Client(discord.Client):
    def __init__(self, *, intents: Intents, **options: Any) -> None:
        super().__init__(intents=intents, **options)
        self.squad_who_command = None
        self.ps_who_command = None

    async def setup_hook(self) -> None:
        await super().setup_hook()
        self.register_commands()
        self.register_reaction_handlers()
        self.register_background_tasks()

    def register_commands(self):
        """Register all available commands."""
        self.register_command(commands.ChatCommand)
        self.register_command(commands.GenerateImageCommand)
        squad_who_command = self.register_command(
            commands.WhoCommand, 'squad', config.DISCORD_SQUAD_CHANNEL_ID
        )
        ps_who_command = self.register_command(
            commands.WhoCommand, 'postscriptum', config.DISCORD_POSTSCRIPTUM_CHANNEL_ID
        )
        self.register_command(commands.F1CreateEventsCommand)
        self.register_command(commands.CreateEvents)
        self.register_command(commands.DeleteEvents)
        self.register_command(commands.TtsCommand)

        self.squad_who_command = squad_who_command
        self.ps_who_command = ps_who_command

    def register_command(self, command_class, *args, **kwargs) -> BaseCommand:
        """Register a command class."""
        command = command_class(self, *args, **kwargs)
        COMMANDS.append(command)
        return command

    def register_reaction_handlers(self):
        """Register all available reaction handlers."""

    def register_reaction_handler(self, handler_class):
        """Register a reaction handler class."""
        command = handler_class(self)
        REACTION_HANDLERS.append(command)

    def register_background_tasks(self):
        """Register all background tasks."""
        self.loop.create_task(background_tasks.AstronomyPictureOfTheDayTask(self).start())
        self.loop.create_task(background_tasks.BattlemetricsPlayersTask(self).start())
        self.loop.create_task(background_tasks.DeleteChatConversations(self).start())
        self.loop.create_task(background_tasks.F1DaySchedule(self).start())
        self.loop.create_task(background_tasks.F1RaceWeek(self).start())
        self.loop.create_task(background_tasks.F1Results(self).start())
        self.loop.create_task(background_tasks.HackerNewsTask(self).start())
        self.loop.create_task(background_tasks.LiveUaMap(self).start())
        self.loop.create_task(background_tasks.NewsMinimalistTask(self).start())
        self.loop.create_task(background_tasks.SquadLayersTask(self).start())
        self.loop.create_task(background_tasks.YtsNewMoviesTask(self).start())
