from discord import RawMessageDeleteEvent
from discord.ext import commands
from extensions.logs.functions import on_raw_message_delete


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if payload.guild_id is not None:
            await on_raw_message_delete.log(self.bot, payload)


def setup(bot):
    bot.add_cog(Logs(bot))
