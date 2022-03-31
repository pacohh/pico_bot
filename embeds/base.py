import discord


class BaseEmbed(discord.Embed):
    @classmethod
    async def build(cls, *args, **kwargs):
        raise NotImplementedError()
