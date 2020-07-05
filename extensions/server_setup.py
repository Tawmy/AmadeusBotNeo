import asyncio
import json
import shutil
from os.path import isfile

import discord
from discord.ext import commands

from components import checks
from components.amadeusMenu import AmadeusMenu
from components.amadeusPrompt import AmadeusPrompt


class ServerSetup(commands.Cog):
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
        await self.__prepare_setup_menu(ctx, setup_menu)
        await setup_menu.set_user_specific(True, setup_user)
        result = await setup_menu.show_menu(ctx, 120)
        if result is None:
            return

        # Overwrite config entirely?
        if result[2] == "🟥":
            self.bot.config[str(ctx.guild.id)] = {}
        else:
            self.bot.config.setdefault(str(ctx.guild.id), {})

        setup_prompt = AmadeusPrompt(self.bot, None)
        await setup_prompt.set_user_specific(True, setup_user)

        collected_information = await self.__collect_setup_information(ctx, setup_prompt, result[0])
        # If input chain not successful (cancelled or timeout)
        if collected_information is None:
            return
        # Apply all the previously collected information to server config
        self.bot.config[str(ctx.guild.id)].update(collected_information)
        # Copy default values to server config
        await self.__copy_default_values(ctx)
        # Save server config to json file and give feedback on its success
        if await self.save_config(ctx):
            if str(ctx.guild.id) in self.bot.corrupt_configs:
                self.bot.corrupt_configs.remove(str(ctx.guild.id))
            embed = await self.prepare_status_embed(ctx, True)
            permissions_embed = await self.__check_bot_permissions(ctx)
            for field in permissions_embed.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
        else:
            embed = await self.__prepare_status_embed(False)
        await result[0].edit(embed=embed)

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

    async def __prepare_setup_menu(self, ctx, setup_menu):
        bot_name = self.bot.app_info.name
        string_list = await self.bot.strings.get_string(ctx, "server_setup", "setup_title")
        title = await self.bot.strings.insert_into_string(string_list, bot_name, "left")
        string_list = await self.bot.strings.get_string(ctx, "server_setup", "setup_introduction")
        description = await self.bot.strings.insert_into_string(string_list, [bot_name, bot_name])

        # Different prompt if server has been configured before
        json_file = str(ctx.guild.id) + '.json'
        if isfile('config/' + json_file):
            shutil.copy('config/' + json_file, 'config/backup/' + json_file)
            description += await self.bot.strings.get_string(ctx, "server_setup", "server_configured_before")
            emoji = ["🟦", "🟥"]
        else:
            description += await self.bot.strings.get_string(ctx, "server_setup", "setup_confirm_ready")
            emoji = ["✅"]

        await setup_menu.set_title(title)
        await setup_menu.set_description(description)
        await setup_menu.append_emoji(emoji)

    async def __prepare_prompt(self, setup_prompt, opt_val, status):
        # opt_val is None when no user input is to be prompted
        if opt_obj is not None:
            await setup_prompt.set_author(await self.bot.strings.get_string(ctx, "prompt", "please_enter"))
            cfg_strings = await self.bot.strings.extract_config_strings(ctx, opt_obj)
            await setup_prompt.set_title(cfg_strings[0])
            await setup_prompt.set_description(cfg_strings[1])
        # if input invalid
        if status == 1:
            await setup_prompt.append_description(await self.bot.strings.get_string(ctx, "prompt", "error_not_found"))
        # if setup cancelled
        elif status == 2:
            await setup_prompt.set_description(await self.bot.strings.get_string(ctx, "server_setup", "setup_cancelled"))

    async def prepare_status_embed(self, ctx, successful_bool):
        embed = discord.Embed()
        if successful_bool:
            embed.title = await self.bot.strings.get_string(ctx, "server_setup", "setup_successful")
            string = await self.bot.strings.get_string(ctx, "server_setup", "setup_successful_description")
            embed.description = await self.bot.strings.insert_into_string(string, self.bot.app_info.name)
        else:
            embed.title = await self.bot.strings.get_string(ctx, "server_setup", "setup_error_save_config")
        return embed

    async def __collect_setup_information(self, ctx, setup_prompt, setup_message):
        collected_information = {}
        # Iterate categories
        for cat_key, cat_val in self.bot.values.options.items():
            # Only iterate essential categories
            if cat_key.startswith("essential_"):
                collected_information[cat_key] = {}
                # Iterate options in category
                for opt_key, opt_val in self.bot.values.options[cat_key]["list"].items():
                    await self.prepare_prompt(ctx, setup_prompt, opt_val, 0)
                    obj = None
                    while obj is None:
                        result = await setup_prompt.show_prompt(ctx, 120, setup_message)
                        # If user has not cancelled
                        if result is not None:
                            obj = await self.__check_input(ctx, cat_key, result[1])
                            # if input invalid
                            if obj is None:
                                await self.__prepare_prompt(setup_prompt, opt_val, 1)
                            else:
                                collected_information[cat_key].setdefault(opt_key, obj.id)
                        # If user has cancelled
                        else:
                            await self.__prepare_prompt(setup_prompt, None, 2)
                            return None
        return collected_information

    async def __check_input(self, ctx, cat_key, user_input):
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

    async def __copy_default_values(self, ctx):
        # Iterate categories
        for cat_key, cat_val in self.bot.values.options.items():
            # Only iterate non-essential categories
            if not cat_key.startswith("essential_"):
                self.bot.config[str(ctx.guild.id)].setdefault(cat_key, {})
                # Iterate options in category
                for opt_key, opt_val in self.bot.values.options[cat_key]["list"].items():
                    # Set option for server if not already set
                    self.bot.config[str(ctx.guild.id)][cat_key].setdefault(
                        opt_key, self.bot.values.options[cat_key]["list"][opt_key]["default"])

    async def __check_bot_permissions(self, ctx):
        embed = discord.Embed()
        for ch_key, ch_val in self.bot.config[str(ctx.guild.id)]["essential_channels"].items():
            channel = ctx.guild.get_channel(ch_val)
            permissions_have = channel.permissions_for(ctx.guild.me)
            permissions_need = self.bot.values.options["essential_channels"]["list"][ch_key]["permissions"]
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
    bot.add_cog(ServerSetup(bot))
