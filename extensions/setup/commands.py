import copy

import discord
from discord.ext import commands

from components import checks
from extensions.setup.enums import SetupType, SetupStatus
from extensions.setup.functions import setup as setup_functions
from extensions.config import helper as c


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_emoji = ["✅", "🟦", "🟥"]

    @commands.command(name='setup')
    @commands.check(checks.is_guild_owner)
    @commands.check(checks.block_dms)
    async def setup(self, ctx, setup_user: discord.Member = None):
        if setup_user is None:
            setup_user = ctx.author

        menu = await setup_functions.prepare_setup_type_selection_menu(ctx, self.setup_emoji)
        await menu.set_user_specific(True, setup_user)
        setup_type_selection = await setup_functions.ask_for_setup_type(ctx, menu, self.setup_emoji)
        if setup_type_selection.setup_type == SetupType.CANCELLED:
            embed = await setup_functions.prepare_status_embed(ctx, SetupStatus.CANCELLED)
            return await setup_type_selection.message.edit(embed=embed)

        # copy current config to later apply if cancelled
        backed_up_config = copy.deepcopy(self.bot.config.get(str(ctx.guild.id)))

        await setup_functions.initialise_guild_config(ctx, setup_type_selection.setup_type)
        all_successful_bool = await setup_functions.iterate_config_options(ctx, setup_user, setup_type_selection.message)

        await setup_functions.add_default_limits(ctx)

        if all_successful_bool:
            await setup_functions.set_bot_enabled(ctx)
            save_successful_bool = await c.save_config(ctx)
            setup_status = SetupStatus.SUCCESSFUL if save_successful_bool else SetupStatus.SAVE_FAILED
        else:
            setup_status = SetupStatus.CANCELLED

        embed = await setup_functions.prepare_status_embed(ctx, setup_status)

        if setup_status == SetupStatus.SUCCESSFUL:
            embed = await setup_functions.check_bot_permissions(ctx, embed)
            embed = await setup_functions.add_default_limits_to_embed(ctx, embed)
        elif setup_status == SetupStatus.CANCELLED and setup_type_selection.setup_type == SetupType.REGULAR:
            self.bot.config[str(ctx.guild.id)] = backed_up_config
        await setup_type_selection.message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Setup(bot))
