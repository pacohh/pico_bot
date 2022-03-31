import discord

from embeds.base import BaseEmbed
from utils.datetime import format_british_now
from utils.formatting import code_block


class WhoEmbed(BaseEmbed):
    @classmethod
    async def build(cls, server: dict) -> None:
        embed = cls(
            title=f":flag_{server['country']}: {server['name']}",
            color=discord.Color.dark_red(),
        )
        embed.add_field(
            name='Pepegas',
            value=code_block(', '.join(server['pepegas'])),
            inline=False,
        )
        embed.add_field(
            name='Layer',
            value=code_block(server['layer']),
            inline=True,
        )
        embed.add_field(
            name='Players',
            value=code_block(f"{server['players']}/{server['max_players']} (+{server['queue']})"),
            inline=True,
        )

        embed.set_footer(text=f'!who | {format_british_now()}')
        return embed
