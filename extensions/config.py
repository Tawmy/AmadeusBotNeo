from dataclasses import dataclass
from enum import Enum

import discord
from discord.ext import commands
from components import amadeusMenu, amadeusPrompt, checks, strings as s, config
from components.amadeusMenu import AmadeusMenuStatus
from components.amadeusPrompt import AmadeusPromptStatus
from components.config import ConfigStatus, InputType


class ConfigStep(Enum):
    NO_INFO = 0
    CATEGORY = 1
    OPTION = 2
    CATEGORY_OPTION = 3
    CATEGORY_OPTION_CONFIRMED = 4
    CATEGORY_OPTION_CANCELLED = 5
    CATEGORY_OPTION_VALUE = 6
    CATEGORY_OPTION_SETDEFAULT = 7
    FINISHED = 10


@dataclass
class InputData:
    configStep: ConfigStep = ConfigStep.NO_INFO
    message: discord.message = None
    category: str = None
    option: str = None
    values: list = None


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='config')
    @commands.check(checks.block_dms)
    async def config(self, ctx, *args):
        input_data = InputData()
        if len(args) > 0:
            await self.check_input(ctx, args, input_data)
        await self.collect_config_data(ctx, input_data)
        if input_data.configStep == ConfigStep.CATEGORY_OPTION_VALUE:
            await self.__check_value_data(ctx, input_data)

    async def check_input(self, ctx, args, input_data):
        category = await self.get_category(ctx, args[0])
        if category is not None:
            input_data.category = category
            if len(args) > 1:
                category, option = await self.get_option(ctx, args[1], category)
                if option is not None:
                    input_data.option = option
                    if len(args) > 2:
                        input_data.values = args[2:]
                        input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
                    else:
                        input_data.configStep = ConfigStep.CATEGORY_OPTION
                else:
                    input_data.configStep = ConfigStep.CATEGORY
            else:
                input_data.configStep = ConfigStep.CATEGORY
        else:
            category, option = await self.get_option(ctx, args[0], category)
            if option is not None:
                input_data.category = category
                input_data.option = option
                if len(args) > 1:
                    input_data.values = args[1:]
                    input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
                else:
                    input_data.configStep = ConfigStep.OPTION
        return input_data

    async def collect_config_data(self, ctx, input_data):
        while input_data.configStep is not ConfigStep.FINISHED:
            if input_data.configStep == ConfigStep.NO_INFO:
                await self.ask_for_category(ctx, input_data)
            elif input_data.configStep == ConfigStep.CATEGORY:
                await self.ask_for_option(ctx, input_data)
            elif input_data.configStep in [ConfigStep.OPTION, ConfigStep.CATEGORY_OPTION]:
                await self.show_info(ctx, input_data)
            elif input_data.configStep == ConfigStep.CATEGORY_OPTION_CONFIRMED:
                await self.ask_for_value(ctx, input_data)
            elif input_data.configStep == ConfigStep.CATEGORY_OPTION_SETDEFAULT:
                await self.set_default_value(ctx, input_data)
                return
            elif input_data.configStep in [ConfigStep.CATEGORY_OPTION_VALUE, ConfigStep.CATEGORY_OPTION_CANCELLED]:
                return

    async def ask_for_category(self, ctx, input_data):
        string = await s.get_string(ctx, "config", "select_category")
        menu = amadeusMenu.AmadeusMenu(self.bot, string.string)
        await menu.set_user_specific(True)
        category_names = []
        for category_key, category_val in self.bot.options.items():
            category_names.append(category_key)
            strings = await s.extract_config_option_strings(ctx, category_val)
            await menu.add_option(strings.name, strings.description)
        menu_data = await menu.show_menu(ctx, 120)
        if menu_data.status is not AmadeusMenuStatus.SELECTED:
            input_data.configStep = ConfigStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.configStep = ConfigStep.CATEGORY
            input_data.message = menu_data.message
            input_data.category = category_names[menu_data.reaction_index]

    async def get_category(self, ctx, user_input):
        user_input = user_input.lower()
        if self.bot.options.get(user_input) is not None:
            return user_input
        else:
            for category_key, category_val in self.bot.options.items():
                if await self.check_value(ctx, category_val, user_input) is True:
                    return category_key
        return None

    async def get_option(self, ctx, user_input, category=None):
        user_input = user_input.lower()
        if category is not None and self.bot.options.get(category, {}).get("list", {}).get(user_input) is not None:
            return category, user_input

        for category_key, category_val in self.bot.options.items():
            for option_key, option_val in category_val.get("list").items():
                if await self.check_value(ctx, option_val, user_input) is True:
                    return category_key, option_key
        return None, None

    async def check_value(self, ctx, value, user_input):
        # check for value name in server language
        lang = await s.get_guild_language(ctx)
        option = value.get("name", {}).get(lang)
        if option is not None and user_input == option.lower():
            return True
        elif lang != self.bot.default_language:
            # if value does not have a name in specified language, check against default language
            option = value.get("name", {}).get(self.bot.default_language)
            if option is not None and user_input == option.lower():
                return True
        return None

    async def ask_for_option(self, ctx, input_data):
        # prepare menu
        category = self.bot.options.get(input_data.category)
        category_values = await s.extract_config_option_strings(ctx, category)
        menu = amadeusMenu.AmadeusMenu(self.bot, category_values.name)
        await menu.set_description(category_values.description)
        await menu.set_user_specific(True)

        await self.__add_footer(ctx, input_data, menu)

        # add options to menu
        option_names = []
        for option_key, option_val in category["list"].items():
            option_names.append(option_key)
            strings = await s.extract_config_option_strings(ctx, option_val)
            await menu.add_option(strings.name, strings.description)

        menu_data = await menu.show_menu(ctx, 120, input_data.message)
        if menu_data.status is not AmadeusMenuStatus.SELECTED:
            input_data.configStep = ConfigStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.configStep = ConfigStep.CATEGORY_OPTION
            input_data.message = menu_data.message
            input_data.option = option_names[menu_data.reaction_index]

    async def show_info(self, ctx, input_data):
        # prepare menu
        option_full = self.bot.options.get(input_data.category).get("list").get(input_data.option)
        option_values = await s.extract_config_option_strings(ctx, option_full)
        menu = amadeusMenu.AmadeusMenu(self.bot, option_values.name)
        await menu.set_description(option_values.description)
        await menu.set_user_specific(True)

        await self.__add_footer(ctx, input_data, menu)

        await self.__add_info_fields_to_info(ctx, input_data, menu, option_full)
        await self.__add_options_to_info(ctx, menu, option_full)

        menu_data = await menu.show_menu(ctx, 120, input_data.message)
        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.configStep = ConfigStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.configStep = ConfigStep.CATEGORY_OPTION_CONFIRMED
            elif menu_data.reaction_index == 1:
                input_data.configStep = ConfigStep.CATEGORY_OPTION_SETDEFAULT

    async def __add_info_fields_to_info(self, ctx, input_data, menu, option_full):
        # add fields to menu
        current_value = await self.__convert_current_value(ctx, input_data.category, input_data.option)

        string = await s.get_string(ctx, "config", "current_value")
        await menu.add_field(string.string, current_value)

        string = await s.get_string(ctx, "config", "default_value")
        default_value = option_full.get("default")
        if default_value is not None:
            await menu.add_field(string.string, default_value)

        # TODO add field about is_list

        await self.__add_valid_field(ctx, menu, input_data.category, input_data.option)

    async def __add_options_to_info(self, ctx, menu, option_full):
        string = await s.get_string(ctx, "config", "option_change")
        await menu.add_option(string.string)
        default_value = option_full.get("default")
        if default_value is not None:
            string = await s.get_string(ctx, "config", "option_setdefault")
            await menu.add_option(string.string)

    async def __add_footer(self, ctx, input_data, menu):
        prefix = ctx.bot.config[str(ctx.guild.id)]["general"]["command_prefix"]
        footer_text = prefix + ctx.command.name + " " + input_data.category
        if input_data.option is not None:
            footer_text = footer_text + " " + input_data.option
        await menu.set_footer_text(footer_text)

    async def ask_for_value(self, ctx, input_data):
        option_full = self.bot.options.get(input_data.category).get("list").get(input_data.option)
        option_values = await s.extract_config_option_strings(ctx, option_full)
        prompt = amadeusPrompt.AmadeusPrompt(self.bot, option_values.name)
        await prompt.set_user_specific(True)
        string = await s.get_string(ctx, "prompt", "please_enter")
        await prompt.set_author(string.string)

        await self.__add_valid_field(ctx, prompt, input_data.category, input_data.option)

        prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)
        if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
            input_data.configStep = ConfigStep.FINISHED
            await prompt.show_result(ctx)
        else:
            input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
            input_data.message = prompt_data.message
            input_data.values = prompt_data.input

    async def set_default_value(self, ctx, input_data):
        prepared_input = await config.set_default_config(ctx, input_data.category, input_data.option)
        await self.__show_config_status(ctx, input_data.message, prepared_input.status)

    async def __convert_current_value(self, ctx, category, option):
        current_value = await config.get_config(ctx, category, option)
        converted_input = await config.prepare_input(ctx, category, option, current_value.value)
        if len(converted_input.list) == 1:
            return converted_input.list[0]
        return converted_input.list

    async def __add_valid_field(self, ctx, menu, category, option):
        valid_input = await config.get_valid_input(ctx, category, option)

        if valid_input.input_type == InputType.ANY:
            return menu

        title = await s.get_string(ctx, "config", "valid_entries")
        for i, item in enumerate(valid_input.valid_list):
            if not isinstance(item, str):
                valid_input.valid_list[i] = str(item)
        value = '\n'.join(valid_input.valid_list)
        await menu.add_field(title.string, value, False)

    async def __check_value_data(self, ctx, input_data):
        prepared_input = await config.prepare_input(ctx, input_data.category, input_data.option, input_data.values)
        # if isinstance(prepared_input, ConfigStatus):
        if prepared_input.status != ConfigStatus.PREPARATION_SUCCESSFUL:
            await self.__show_config_status(ctx, input_data.message, prepared_input.status)
            return
        await config.set_config(ctx, prepared_input)
        await self.__show_config_status(ctx, input_data.message, prepared_input.status)

    async def __show_config_status(self, ctx, message, status):
        embed = discord.Embed()

        string_desc = None
        if status == ConfigStatus.OPTION_DOES_NOT_EXIST:
            string = await s.get_string(ctx, "config_status", "OPTION_DOES_NOT_EXIST")
        elif status == ConfigStatus.CONVERSION_FAILED:
            string = await s.get_string(ctx, "config_status", "CONVERSION_FAILED")
        elif status == ConfigStatus.NOT_IN_VALID_LIST:
            string = await s.get_string(ctx, "config_status", "NOT_IN_VALID_LIST")
            string_desc = await s.get_string(ctx, "config_status", "NOT_IN_VALID_LIST_DESC")
        elif status == ConfigStatus.UNKNOWN_DATA_TYPE:
            string = await s.get_string(ctx, "config_status", "UNKNOWN_DATA_TYPE")
        elif status == ConfigStatus.NOT_VALID_FOR_DATA_TYPE:
            string = await s.get_string(ctx, "config_status", "NOT_VALID_FOR_DATA_TYPE")
            string_desc = await s.get_string(ctx, "config_status", "NOT_VALID_FOR_DATA_TYPE_DESC")
        elif status == ConfigStatus.TEXT_CHANNEL_NOT_FOUND:
            string = await s.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND")
            string_desc = await s.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND_DESC")
        elif status == ConfigStatus.ROLE_NOT_FOUND:
            string = await s.get_string(ctx, "config_status", "ROLE_NOT_FOUND")
            string_desc = await s.get_string(ctx, "config_status", "ROLE_NOT_FOUND_DESC")
        elif status == ConfigStatus.SAVE_SUCCESS:
            string = await s.get_string(ctx, "config_status", "SAVE_SUCCESS")
        elif status == ConfigStatus.SAVE_FAIL:
            string = await s.get_string(ctx, "config_status", "SAVE_FAIL")
        else:
            string = await s.get_string(ctx, "config_status", "OTHER")

        embed.title = string.string
        if string_desc is not None and string_desc.successful:
            embed.description = string_desc.string

        # TODO this needs to be more dynamic, like set_footer in amadeusMenu
        # it works for now because config is always user specific
        name = ctx.author.display_name
        avatar = ctx.author.avatar_url_as(static_format="png")
        embed.set_footer(text=name, icon_url=avatar)

        if message is not None:
            await message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Config(bot))
