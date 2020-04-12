import asyncio
import json
import shutil
from os.path import isfile

import discord
from discord.ext import commands

from components import checks
from components.amadeusMenu import AmadeusMenu
from components.amadeusPrompt import AmadeusPrompt


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='setup')
    @commands.check(checks.is_guild_owner)
    @commands.check(checks.block_dms)
    async def setup(self, ctx, setup_user: discord.Member = "owner_has_not_specified_user"):
        # Guild owner can give another user permission to execute setup
        if setup_user == "owner_has_not_specified_user":
            setup_user = ctx.author

        setup_menu = AmadeusMenu(self.bot, None)
        await self.prepare_setup_menu(ctx, setup_menu)
        await setup_menu.set_user_specific(True, setup_user)
        result = await setup_menu.show_menu(ctx, 120)

        # Overwrite config entirely?
        if result[2] == "🟥":
            self.bot.config[str(ctx.guild.id)] = {}
        else:
            self.bot.config.setdefault(str(ctx.guild.id), {})

        setup_prompt = AmadeusPrompt(self.bot, None)
        await setup_prompt.set_user_specific(True, setup_user)

        collected_information = await self.collect_setup_information(ctx, setup_prompt, result[0])
        # If input chain not successful (cancelled or timeout)
        if collected_information is None:
            return
        # Apply all the previously collected information to server config
        self.bot.config[str(ctx.guild.id)].update(collected_information)
        # Copy default values to server config
        await self.copy_default_values(ctx)
        # Save server config to json file and give feedback on its success
        if await self.save_config(ctx):
            embed = await self.prepare_status_embed(True)
            permissions_embed = await self.check_bot_permissions(ctx)
            for field in permissions_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
        else:
            embed = await self.prepare_status_embed(False)
        await result[0].edit(embed=embed)

    async def prepare_setup_menu(self, ctx, setup_menu):
        bot_name = self.bot.app_info.name
        title = bot_name + " Setup"
        description = "Before " + bot_name + " can do its job, some channels and roles need to be configured. "
        description += bot_name + " will walk you through this process step by step.\n\n"

        # Different prompt if server has been configured before
        json_file = str(ctx.guild.id) + '.json'
        if isfile('config/' + json_file):
            shutil.copy('config/' + json_file, 'config/backup/' + json_file)
            description += "Your server has been configured before. "
            description += "You can choose to either overwrite only the channels and roles set during setup, or "
            description += "reset the configuration **entirely** (❗).\n\n"
            description += "🟦 *Regular setup* **|** 🟥 *Full reset*"
            emoji = ["🟦", "🟥"]
        else:
            description += "Once you are ready, click the ✅ reaction under this message."
            emoji = ["✅"]

        await setup_menu.set_title(title)
        await setup_menu.set_description(description)
        await setup_menu.append_emoji(emoji)

    async def prepare_prompt(self, setup_prompt, opt_val, status):
        # opt_val is None when no user input is to be prompted
        if opt_val is not None:
            await setup_prompt.set_author("Please enter:")
            await setup_prompt.set_title(opt_val["name"])
            await setup_prompt.set_description(opt_val["description"])
        # if input invalid
        if status == 1:
            await setup_prompt.append_description("\n\n⚠ Not found. Please try again.")
        # if setup cancelled
        elif status == 2:
            await setup_prompt.set_description("Setup cancelled")
        elif status == 3:
            await setup_prompt.set_title("Setup successful!")
            description = "You can now use " + self.bot.app_info.name + "!\n\n"
            description += "Below are all the permissions the bot needs in the channels just set up. "
            description += "Please make sure to grant it access to all of these."
            await setup_prompt.set_description(description)
        elif status == 4:
            await setup_prompt.set_title("Could not save config!")

    async def prepare_status_embed(self, successful_bool):
        embed = discord.Embed()
        if successful_bool:
            embed.title = "Setup successful!"
            embed.description = "You can now use " + self.bot.app_info.name + "!\n\n"
            embed.description += "Below are all the permissions the bot needs in the channels just set up. "
            embed.description += "Please make sure to grant it access to all of these."
        else:
            embed.title = "Could not save config!"
        return embed

    async def collect_setup_information(self, ctx, setup_prompt, setup_message):
        collected_information = {}
        # Iterate categories
        for cat_key, cat_val in self.bot.config["options"].items():
            # Only iterate essential categories
            if cat_key.startswith("essential_"):
                collected_information[cat_key] = {}
                # Iterate options in category
                for opt_key, opt_val in self.bot.config["options"][cat_key]["list"].items():
                    await self.prepare_prompt(setup_prompt, opt_val, 0)
                    obj = None
                    while obj is None:
                        result = await setup_prompt.show_prompt(ctx, 120, setup_message)
                        # If user has not cancelled
                        if result[1] not in ["cancel", "\"cancel\""]:
                            obj = await self.check_input(ctx, cat_key, result[1])
                            # if input invalid
                            if obj is None:
                                await self.prepare_prompt(setup_prompt, opt_val, 1)
                            else:
                                collected_information[cat_key].setdefault(opt_key, obj.id)
                        # If user has cancelled
                        else:
                            await self.prepare_prompt(setup_prompt, None, 2)
                            return None
        return collected_information

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
