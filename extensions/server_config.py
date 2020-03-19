import asyncio
import json
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
        # Guild owner can give another user permission to execute setup
        if setup_user == "owner_has_not_specified_user":
            setup_user = ctx.author

        initial_embed_data = await self.prepare_initial_embed(ctx, setup_user)
        setup_message = await ctx.send(embed=initial_embed_data[0])

        if initial_embed_data[1]:
            await setup_message.add_reaction("✅")
        else:
            await setup_message.add_reaction("🟦")
            await setup_message.add_reaction("🟥")

        def check(reaction, user):
            return user == setup_user and setup_message.id == reaction.message.id and reaction.emoji in ["✅", "🟦", "🟥"]
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check)
        except asyncio.TimeoutError:
            await setup_message.clear_reactions()
            embed = await self.prepare_prompt(None, 2)
            await setup_message.edit(embed=embed)
            return
        else:
            await setup_message.clear_reactions()
            # Overwrite config entirely?
            if reaction.emoji == "🟥":
                self.bot.config[str(ctx.guild.id)] = {}
            else:
                self.bot.config.setdefault(str(ctx.guild.id), {})
            collected_information = await self.collect_setup_information(ctx, setup_message, setup_user)
            # If input chain not successful (cancelled or timeout)
            if collected_information is None:
                return
            # Apply all the previously collected information to server config
            self.bot.config[str(ctx.guild.id)].update(collected_information)
            # Copy default values to server config
            await self.copy_default_values(ctx)
            # Save server config to json file and give feedback on its success
            if await self.save_config(ctx):
                embed = await self.prepare_prompt(None, 3)
                permissions_embed = await self.check_bot_permissions(ctx)
                for field in permissions_embed.fields:
                    embed.add_field(name=field.name, value=field.value, inline=field.inline)
            else:
                embed = await self.prepare_prompt(None, 4)
            await setup_message.edit(embed=embed)

    async def prepare_initial_embed(self, ctx, setup_user):
        embed = discord.Embed()
        bot_name = self.bot.app_info.name
        embed.title = bot_name + " Setup"
        embed.description = "Before " + bot_name + " can do its job, some channels and roles need to be configured. "
        embed.description += bot_name + " will walk you through this process step by step.\n\n"
        embed.set_footer(text=setup_user.display_name, icon_url=setup_user.avatar_url_as(static_format="png"))

        # Different prompt if server has been configured before
        is_initial_config = True
        json_file = str(ctx.guild.id) + '.json'
        if isfile('config/' + json_file):
            shutil.copy('config/' + json_file, 'config/backup/' + json_file)
            is_initial_config = False
            embed.description += "Your server has been configured before. "
            embed.description += "You can choose to either overwrite only the channels and roles set during setup, or "
            embed.description += "reset the configuration **entirely** (❗).\n\n"
            embed.description += "🟦 *Regular setup* **|** 🟥 *Full reset*"
        else:
            embed.description += "Once you are ready, click the ✅ reaction under this message."

        return [embed, is_initial_config]

    async def prepare_prompt(self, opt_val, status):
        embed = discord.Embed()
        # opt_val is None when no user input is to be prompted
        if opt_val is not None:
            embed.set_author(name="Please enter:")
            embed.title = opt_val["name"]
            embed.description = opt_val["description"]
            embed.set_footer(text="Type \"cancel\" to cancel")
        # if input invalid
        if status == 1:
            embed.description += "\n\n⚠ Not found. Please try again."
        # if setup cancelled
        elif status == 2:
            embed.title = "Setup cancelled"
        elif status == 3:
            embed.title = "Setup successful!"
            embed.description = "You can now use " + self.bot.app_info.name + "!\n\n"
            embed.description += "Below are all the permissions the bot needs in the channels just set up. "
            embed.description += "Please make sure to grant it access to all of these."
        elif status == 4:
            embed.title = "Could not save config!"
        return embed

    async def collect_setup_information(self, ctx, setup_message, setup_user):
        collected_information = {}
        # Iterate categories
        for cat_key, cat_val in self.bot.config["options"].items():
            # Only iterate essential categories
            if cat_key.startswith("essential_"):
                collected_information[cat_key] = {}
                # Iterate options in category
                for opt_key, opt_val in self.bot.config["options"][cat_key]["list"].items():
                    embed = await self.prepare_prompt(opt_val, 0)
                    obj = None
                    while obj is None:
                        user_input = await self.await_input(ctx, embed, setup_message, setup_user)
                        # If user has not cancelled
                        if user_input not in ["cancel", "\"cancel\""]:
                            obj = await self.check_input(ctx, cat_key, user_input)
                            # if input invalid
                            if obj is None:
                                embed = await self.prepare_prompt(opt_val, 1)
                                await setup_message.edit(embed=embed)
                            else:
                                collected_information[cat_key].setdefault(opt_key, obj.id)
                        # If user has cancelled
                        else:
                            embed = await self.prepare_prompt(None, 2)
                            await setup_message.edit(embed=embed)
                            return None
        return collected_information

    async def await_input(self, ctx, embed, setup_message, setup_user):
        await setup_message.edit(embed=embed)

        def check(msg):
            return msg.author is setup_user and msg.channel is ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=180.0, check=check)
        except asyncio.TimeoutError:
            await self.prepare_prompt(None, 1)
        else:
            await msg.delete()
            return msg.content

    async def check_input(self, ctx, cat_key, user_input):
        if cat_key == "essential_channels":
            try:
                return await commands.TextChannelConverter().convert(ctx, user_input)
            except commands.CommandError:
                return None
        elif cat_key == "essential_roles":
            try:
                return await commands.RoleConverter().convert(ctx, user_input)
            except commands.CommandError:
                return None

    async def copy_default_values(self, ctx):
        # Iterate categories
        for cat_key, cat_val in self.bot.config["options"].items():
            # Only iterate non-essential categories
            if not cat_key.startswith("essential_"):
                self.bot.config[str(ctx.guild.id)].setdefault(cat_key, {})
                # Iterate options in category
                for opt_key, opt_val in self.bot.config["options"][cat_key].items():
                    # Set option for server if not already set
                    self.bot.config[str(ctx.guild.id)][cat_key].setdefault(opt_key, self.bot.config["options"][cat_key][opt_key]["default"])

    async def save_config(self, ctx):
        json_file = 'config/' + str(ctx.guild.id) + '.json'
        save_status = False
        retries = 4
        while save_status is False and retries > 0:
            with open(json_file, 'w+') as file:
                try:
                    json.dump(self.bot.config[str(ctx.guild.id)], file)
                    return True
                except Exception as e:
                    print(e)
            retries -= 1
            await asyncio.sleep(1)
        return False

    async def check_bot_permissions(self, ctx):
        embed = discord.Embed()
        for ch_key, ch_val in self.bot.config[str(ctx.guild.id)]["essential_channels"].items():
            channel = ctx.guild.get_channel(ch_val)
            permissions_have = channel.permissions_for(ctx.guild.me)
            permissions_need = self.bot.config["options"]["essential_channels"]["list"][ch_key]["permissions"]
            permissions_embed = ""
            for permission in permissions_need:
                if getattr(permissions_have, permission) is True:
                    permissions_embed += "✅ " + permission + "\n"
                else:
                    permissions_embed += "❌ " + permission + "\n"
            if len(permissions_embed) > 0:
                embed.add_field(name="#" + str(channel), value=permissions_embed)
        return embed


def setup(bot):
    bot.add_cog(Config(bot))
