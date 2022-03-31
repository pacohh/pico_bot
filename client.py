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
        self.register_command(commands.WhoCommand)

    def register_command(self, command_class):
        """Register a command class."""
        command = command_class(self)
        COMMANDS.append(command)

    def register_reaction_handlers(self):
        """Register all available reaction handlers."""
        self.register_reaction_handler(commands.WhoRefreshReactionHandler)

    def register_reaction_handler(self, handler_class):
        """Register a reaction handler class."""
        command = handler_class(self)
        REACTION_HANDLERS.append(command)

    def register_background_tasks(self):
        """Register all background tasks."""
        self.loop.create_task(background_tasks.BattlemetricsPlayersTask(self).start())
        self.loop.create_task(background_tasks.PresenceTask(self).start())
