import logging

from background_tasks import bm_players
from bot import client
from commands.base import BaseCommand, BaseReactionHandler
from commands.mixins import DeletePreviousMixin
from components import emojis
from embeds.who import WhoEmbed

REFRESH_EMOJI = emojis.REFRESH

logger = logging.getLogger(__name__)


embed_responses = {}


class WhoCommand(DeletePreviousMixin, BaseCommand):
    command = '!who'
    allow_pm = False

    async def handle(self, message, response_channel):
        servers = bm_players.servers_data
        response = None

        global embed_responses
        embed_responses = {}
        for server in servers:
            embed = await WhoEmbed.build(server)
            response = await response_channel.send(embed=embed)
            embed_responses[server['id']] = response

        if response:
            await response.add_reaction(REFRESH_EMOJI)
            return response


class WhoRefreshReactionHandler(BaseReactionHandler):
    emoji = REFRESH_EMOJI

    async def should_handle(self, reaction, user):
        # Reacted message needs to have an embed
        if not reaction.message.embeds:
            return False

        # Check that the embed is for a !server command
        embed = reaction.message.embeds[0]
        footer = embed.to_dict().get('footer', {}).get('text', '')
        if not footer.startswith(WhoCommand.command):
            return False

        return await super().should_handle(reaction, user)

    async def handle(self, reaction, user, response_channel):
        # Log
        channel = reaction.message.channel
        logger.info('%s triggered !server refresh in #%s', user, channel.name or channel.id)

        # Remove reaction
        await reaction.message.remove_reaction(reaction.emoji, user)

        # Get the old and new server ids
        old_server_ids = set(embed_responses.keys())
        new_server_ids = {server['id'] for server in bm_players.servers_data}

        # If there are new servers then we delete all old embeds and post new ones
        are_new_servers = bool(new_server_ids - old_server_ids)
        if are_new_servers:
            for message in embed_responses.values():
                await message.delete()
                await WhoCommand(client).handle(None, message.channel)
            return

        # Delete the embeds of servers that no longer have players
        empty_server_ids = old_server_ids - new_server_ids
        for server_id in empty_server_ids:
            if server_id in embed_responses:
                await embed_responses[server_id].delete()
                del embed_responses[server_id]
        if empty_server_ids and embed_responses:
            last_message = list(embed_responses.values())[-1]
            await last_message.add_reaction(REFRESH_EMOJI)

        # Update the embeds
        servers = {server['id']: server for server in bm_players.servers_data}
        for server_id in servers:
            message = embed_responses[server_id]
            embed = await WhoEmbed.build(servers[server_id])
            await message.edit(embed=embed)
