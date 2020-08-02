import copy
import shutil
from dataclasses import dataclass
from enum import Enum
from os.path import isfile

import discord
from discord.ext import commands

from components import checks, strings as s, config as c
from components.amadeusMenu import AmadeusMenu, AmadeusMenuStatus
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptStatus
from components.config import ConfigStatus, PreparedInput


class SetupType(Enum):
    REGULAR = 0
    FULL_RESET = 1
    CANCELLED = 2


class InputType(Enum):
    NONE = 0
    OK = 1
    WRONG = 2
    CANCELLED = 3


class SetupStatus(Enum):
    CANCELLED = 0
    SUCCESSFUL = 1
    SAVE_FAILED = 2


@dataclass
class SetupTypeSelection:
    message: discord.Message
    setup_type: SetupType = None


@dataclass
class UserInput:
    type: InputType = InputType.NONE
    prepared_input: PreparedInput = None


class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_emoji = ["✅", "🟦", "🟥"]

    @commands.command(name='setup')
    @commands.check(checks.is_guild_owner)
    @commands.check(checks.block_dms)
    async def setup(self, ctx, setup_user: discord.Member = None):
        if setup_user is None:
            setup_user = ctx.author

        menu = await self.__prepare_setup_type_selection_menu(ctx)
        await menu.set_user_specific(True, setup_user)
        setup_type_selection = await self.__ask_for_setup_type(ctx, menu)
        if setup_type_selection.setup_type == SetupType.CANCELLED:
            embed = await self.__prepare_status_embed(ctx, SetupStatus.CANCELLED)
            return await setup_type_selection.message.edit(embed=embed)

        # copy current config to later apply if cancelled
        backed_up_config = copy.deepcopy(self.bot.config.get(str(ctx.guild.id)))

        await self.__initialise_guild_config(ctx, setup_type_selection.setup_type)
        all_successful_bool = await self.__iterate_config_options(ctx, setup_user, setup_type_selection.message)

        if all_successful_bool:
            await self.__set_bot_enabled(ctx)
            save_successful_bool = await c.save_config(ctx)
            setup_status = SetupStatus.SUCCESSFUL if save_successful_bool else SetupStatus.SAVE_FAILED
        else:
            setup_status = SetupStatus.CANCELLED

        embed = await self.__prepare_status_embed(ctx, setup_status)

        if setup_status == SetupStatus.SUCCESSFUL:
            embed = await self.__check_bot_permissions(ctx, embed)
        elif setup_status == SetupStatus.CANCELLED and setup_type_selection.setup_type == SetupType.REGULAR:
            self.bot.config[str(ctx.guild.id)] = backed_up_config
        await setup_type_selection.message.edit(embed=embed)

    async def __prepare_setup_type_selection_menu(self, ctx) -> AmadeusMenu:
        string = await s.get_string(ctx, "server_setup", "setup_title")
        string_combination = await s.insert_into_string([self.bot.app_info.name], [string.string], s.InsertPosition.LEFT)
        title = string_combination.string_combined

        string = await s.get_string(ctx, "server_setup", "setup_introduction")
        string_combination = await s.insert_into_string([self.bot.app_info.name, self.bot.app_info.name], string.list)
        description = string_combination.string_combined

        # Different prompt if server has been configured before
        # Backup current config to subdirectory
        json_file = str(ctx.guild.id) + '.json'
        if isfile('config/' + json_file):
            shutil.copy('config/' + json_file, 'config/backup/' + json_file)
            string = await s.get_string(ctx, "server_setup", "server_configured_before")
            description += string.string
            emoji = [self.setup_emoji[1], self.setup_emoji[2]]
        else:
            string = await s.get_string(ctx, "server_setup", "setup_confirm_ready")
            description += string.string
            emoji = [self.setup_emoji[0]]

        menu = AmadeusMenu(self.bot, title)
        await menu.set_description(description)
        await menu.append_emoji(emoji)
        return menu

    async def __ask_for_setup_type(self, ctx, menu: AmadeusMenu) -> SetupTypeSelection:
        result = await menu.show_menu(ctx, 120)
        setup_type_selection = SetupTypeSelection(result.message)
        if result.status == AmadeusMenuStatus.SELECTED:
            if result.reaction_emoji in [self.setup_emoji[0], self.setup_emoji[1]]:
                setup_type_selection.setup_type = SetupType.REGULAR
            elif result.reaction_emoji == self.setup_emoji[2]:
                setup_type_selection.setup_type = SetupType.FULL_RESET
        else:
            setup_type_selection.setup_type = SetupType.CANCELLED
        return setup_type_selection

    async def __initialise_guild_config(self, ctx, setup_type: SetupType):
        # delete config if reset emoji clicked
        if setup_type == SetupType.FULL_RESET:
            self.bot.config[str(ctx.guild.id)] = {}
        else:
            self.bot.config.setdefault(str(ctx.guild.id), {})

    async def __iterate_config_options(self, ctx, setup_user: discord.User, message: discord.Message) -> bool:
        # Iterate categories
        for category_key, category_values in self.bot.options.items():
            # Iterate options in category
            for option_key, option_values in self.bot.options[category_key]["list"].items():
                if option_values["is_essential"]:
                    user_input = await self.__ask_for_value(ctx, category_key, option_key, option_values, setup_user, message)
                    if user_input.type == InputType.CANCELLED:
                        return False
                    await c.set_config(ctx, user_input.prepared_input, False)
        return True

    async def __ask_for_value(self, ctx, c_key: str, o_key: str, o_val: dict, setup_user: discord.User, message: discord.Message) -> UserInput:
        user_input = UserInput()

        option_strings = await s.extract_config_option_strings(ctx, o_val)
        prompt = AmadeusPrompt(self.bot, option_strings.name)
        await prompt.set_description(option_strings.description)
        await prompt.set_user_specific(True, setup_user)
        while True:
            if user_input.type == InputType.WRONG:
                string = await s.get_string(ctx, "prompt", "error_not_found")
                await prompt.append_description(string.string)
            prompt_data = await prompt.show_prompt(ctx, 120, message)
            if prompt_data.status in [AmadeusPromptStatus.CANCELLED, AmadeusPromptStatus.TIMEOUT]:
                user_input.type = InputType.CANCELLED
                break
            prepared_input = await c.prepare_input(ctx, c_key, o_key, prompt_data.input)
            if prepared_input.status == ConfigStatus.PREPARATION_SUCCESSFUL:
                user_input.prepared_input = prepared_input
                user_input.type = InputType.OK
                break
            else:
                user_input.type = InputType.WRONG
        return user_input

    async def __prepare_status_embed(self, ctx, setup_status: SetupStatus):
        embed = discord.Embed()
        if setup_status == SetupStatus.SUCCESSFUL:
            string = await s.get_string(ctx, "server_setup", "setup_successful")
            embed.title = string.string
            string = await s.get_string(ctx, "server_setup", "setup_successful_description")
            string_combination = await s.insert_into_string([self.bot.app_info.name], string.list)
            embed.description = string_combination.string_combined
        elif setup_status == SetupStatus.SAVE_FAILED:
            string = await s.get_string(ctx, "server_setup", "setup_error_save_config")
            embed.title = string.string
        elif setup_status == SetupStatus.CANCELLED:
            string = await s.get_string(ctx, "server_setup", "setup_cancelled")
            embed.title = string.string
        return embed

    async def __check_bot_permissions(self, ctx, embed) -> discord.Embed:
        for ch_key, ch_val in self.bot.config[str(ctx.guild.id)]["essential_channels"].items():
            channel = ctx.guild.get_channel(ch_val)
            permissions_have = channel.permissions_for(ctx.guild.me)
            permissions_need = self.bot.options["essential_channels"]["list"][ch_key]["permissions"]
            permissions_embed = ""
            for permission in permissions_need:
                if getattr(permissions_have, permission) is True:
                    permissions_embed += "✅ " + permission + "\n"
                else:
                    permissions_embed += "❌ " + permission + "\n"
            if len(permissions_embed) > 0:
                embed.add_field(name="#" + str(channel), value=permissions_embed)
        return embed

    async def __set_bot_enabled(self, ctx):
        prepared_input = await c.prepare_input(ctx, "general", "enabled", True)
        if str(ctx.guild.id) in self.bot.corrupt_configs:
            self.bot.corrupt_configs.remove(str(ctx.guild.id))
        await c.set_config(ctx, prepared_input, False)


def setup(bot):
    bot.add_cog(ServerSetup(bot))
