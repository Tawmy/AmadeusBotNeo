from discord.ext import commands
from discord.ext.commands import Context

from components import checks
from extensions.config.dataclasses import InputData, ConfigStep
from extensions.config.functions import config as functions


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='config')
    @commands.check(checks.block_dms)
    async def config(self, ctx: Context, *args):
        input_data = InputData()
        if len(args) > 0:
            await functions.check_input(ctx, args, input_data)
        await functions.collect_config_data(ctx, input_data)
        if input_data.configStep == ConfigStep.CATEGORY_OPTION_VALUE:
            await functions.check_value_data(ctx, input_data)


def setup(bot):
    bot.add_cog(Config(bot))
