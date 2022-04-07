import asyncio

import discord


class ConfirmationMessage:
    def __init__(
        self,
        client: discord.Client,
        channel: discord.TextChannel,
        user: discord.Member,
        text: str,
        timeout: int = 20,
    ) -> None:
        self.client = client
        self.channel = channel
        self.user = user
        self.text = text
        self.timeout = timeout

    async def ask(self):
        # Send confirmation message
        message = await self.channel.send(self.text)
        await message.add_reaction('✅')
        await message.add_reaction('❌')

        def check(reaction_, user):
            is_author = user == self.user
            is_message = reaction_.message.id == message.id
            is_emoji = str(reaction_.emoji) in ['✅', '❌']
            return all([is_author, is_message, is_emoji])

        # Wait for confirmation
        try:
            reaction, _ = await self.client.wait_for(
                'reaction_add',
                timeout=self.timeout,
                check=check,
            )
            return reaction.emoji == '✅'
        except asyncio.TimeoutError:
            pass
        finally:
            # Delete confirmation message
            await message.delete()
