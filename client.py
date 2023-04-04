from __future__ import annotations

import discord

import background_tasks
import commands

COMMANDS = []
REACTION_HANDLERS = []


class Client(discord.Client):
    async def setup_hook(self) -> None:
        await super().setup_hook()
        self.register_commands()
        self.register_reaction_handlers()
        self.register_background_tasks()

    def register_commands(self):
        """Register all available commands."""
        self.register_command(commands.ChatCommand)
        self.register_command(commands.WhoCommand)
        self.register_command(commands.FinanceCandleChartCommand)
        self.register_command(commands.FinanceLineChartCommand)
        self.register_command(commands.F1CreateEventsCommand)
        self.register_command(commands.CreateEvents)
        self.register_command(commands.DeleteEvents)

    def register_command(self, command_class):
        """Register a command class."""
        command = command_class(self)
        COMMANDS.append(command)

    def register_reaction_handlers(self):
        """Register all available reaction handlers."""

    def register_reaction_handler(self, handler_class):
        """Register a reaction handler class."""
        command = handler_class(self)
        REACTION_HANDLERS.append(command)

    def register_background_tasks(self):
        """Register all background tasks."""
        self.loop.create_task(background_tasks.BattlemetricsPlayersTask(self).start())
        self.loop.create_task(background_tasks.DeleteChatConversations(self).start())
        self.loop.create_task(background_tasks.RarbgNewMoviesTask(self).start())
