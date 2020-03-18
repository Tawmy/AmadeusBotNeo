import asyncio
import shutil
from os.path import isfile

import discord
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setup')
    @commands.is_owner()
    async def setup(self, ctx, setup_user: discord.Member = "owner_has_not_specified_user"):
        if setup_user == "owner_has_not_specified_user":
            setup_user = ctx.author

        initial_embed_data = await self.prepare_initial_embed(ctx, setup_user)
        setup_message = await ctx.send(embed=initial_embed_data[0])

        if initial_embed_data[1] is False:
            if self.bot.config["bot"]["debug"]:
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(20)

        await setup_message.add_reaction("✅")

        def check(reaction, user):
            return user == setup_user and setup_message.id == reaction.message.id and reaction.emoji == "✅"
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await setup_message.clear_reactions()
            return
        else:
            await setup_message.clear_reactions()
            await self.collect_setup_information(ctx, initial_embed_data[0], setup_message, setup_user)

    async def prepare_initial_embed(self, ctx, setup_user):
        embed = discord.Embed()
        bot_name = self.bot.app_info.name
        embed.title = bot_name + " Setup"
        embed.description = "Before " + bot_name + " can do its job, some channels and roles need to be configured. "
        embed.description += bot_name + " will walk you through this process step by step.\n\n"
        embed.description += "Once you are ready, click the ✅ reaction under this message."
        embed.set_footer(text=setup_user.display_name, icon_url=setup_user.avatar_url_as(static_format="png"))

        is_initial_config = True
        json_file = str(ctx.guild.id) + '.json'
        if isfile('config/' + json_file):
            shutil.copy('config/' + json_file, 'config/backup/' + json_file)
            is_initial_config = False
            embed.description += " This will only show after 20 seconds because:\n\n"
            embed.description += "!! THIS WILL RESET YOUR SERVER CONFIGURATION ENTIRELY !!"

        return [embed, is_initial_config]

    async def collect_setup_information(self, ctx, embed, setup_message, setup_user):
        # TODO
        pass

    async def prompt_channels(self, ctx):
        for channel in self.bot.config["options"]["essential_channels"]["list"].values():
            prompt_embed = await self.prepare_prompt(channel)
            await ctx.send(embed=prompt_embed)

    async def prepare_prompt(self, channel):
        embed = discord.Embed()
        embed.set_author(name="Please enter:")
        embed.title = channel["name"]
        embed.description = channel["description"]
        embed.set_footer(text="Type \"cancel\" to cancel")
        return embed


def setup(bot):
    bot.add_cog(Config(bot))
