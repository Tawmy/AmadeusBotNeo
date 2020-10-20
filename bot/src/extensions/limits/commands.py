from discord.ext import commands
from discord.ext.commands import Context

from components import checks
from extensions.limits.dataclasses import InputData
from extensions.limits.functions import limits


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='limits')
    @commands.check(checks.block_dms)
    async def limits(self, ctx: Context, *args):
        input_data = InputData()
        if len(args) > 0:
            await limits.check_input(ctx, args, input_data)
        await limits.collect_limits_data(ctx, input_data)


def setup(bot):
    bot.add_cog(Config(bot))
