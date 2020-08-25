import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers import startup
from helpers.startup import DatabaseStatus


class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='reconnect')
    @commands.is_owner()
    async def reconnect(self, ctx: Context):
        ctx.db_session = None
        async with ctx.typing():
            status = await startup.connect_database(ctx.bot)
            embed = discord.Embed()
            if status == DatabaseStatus.CONNECTED:
                title = "Database connected"
            elif status == DatabaseStatus.UPGRADED:
                title = "Database upgraded"
            else:
                title = "Connection failed"
            embed.title = title
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Database(bot))
