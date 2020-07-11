from dataclasses import dataclass
from enum import Enum

import discord
from discord.ext import commands
from components import amadeusMenu, amadeusPrompt, checks, strings as s
from components.enums import ConfigStatus, AmadeusMenuStatus, AmadeusPromptStatus


class ConfigStep(Enum):
    NO_INFO = 0
    CATEGORY = 1
    OPTION = 2
    CATEGORY_OPTION = 3
    CATEGORY_OPTION_VALUE = 4
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
                await self.show_info_and_ask_for_value(ctx, input_data)
            elif input_data.configStep == ConfigStep.CATEGORY_OPTION_VALUE:
                return

    async def ask_for_category(self, ctx, input_data):
        string = s.String("config", "select_category")
        await s.get_string(ctx, string)
        menu = amadeusMenu.AmadeusMenu(self.bot, string.string)
        await menu.set_user_specific(True)
        category_names = []
        for category_key, category_val in self.bot.values.options.items():
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
        if self.bot.values.options.get(user_input) is not None:
            return user_input
        else:
            for category_key, category_val in self.bot.values.options.items():
                if await self.check_value(ctx, category_val, user_input) is True:
                    return category_key
        return None

    async def get_option(self, ctx, user_input, category=None):
        user_input = user_input.lower()
        if category is not None and self.bot.values.options.get(category, {}).get("list", {}).get(user_input) is not None:
            return category, user_input

        for category_key, category_val in self.bot.values.options.items():
            for option_key, option_val in category_val.get("list").items():
                if await self.check_value(ctx, option_val, user_input) is True:
                    return category_key, option_key
        return None, None

    async def check_value(self, ctx, value, user_input):
        # check for value name in server language
        lang = await s.get_language(ctx)
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
        category = self.bot.values.options.get(input_data.category)
        category_values = await s.extract_config_option_strings(ctx, category)
        menu = amadeusMenu.AmadeusMenu(self.bot, category_values.name)
        await menu.set_description(category_values.description)
        await menu.set_user_specific(True)

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

    async def show_info_and_ask_for_value(self, ctx, input_data):

        # prepare prompt
        option_full = self.bot.values.options.get(input_data.category).get("list").get(input_data.option)
        option_values = await s.extract_config_option_strings(ctx, option_full)
        prompt = amadeusPrompt.AmadeusPrompt(self.bot, option_values.name)
        await prompt.set_description(option_values.description)
        await prompt.set_user_specific(True)

        # add fields to prompt

        current_value = await self.__convert_current_value(ctx, input_data.category, input_data.option)

        string = await s.get_string(ctx, s.String("config", "current_value"))
        await prompt.add_field(string.string, current_value)

        string = await s.get_string(ctx, s.String("config", "default_value"))
        default_value = option_full.get("default")
        if default_value is not None:
            await prompt.add_field(string.string, default_value)

        # TODO add field about is_list

        prompt = await self.__add_valid_field(ctx, prompt, input_data.category, input_data.option)

        string = await s.get_string(ctx, s.String("config", "internal_name"))
        await prompt.add_field(string.string, input_data.option)

        prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)
        if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
            input_data.configStep = ConfigStep.FINISHED
            await prompt.show_result(ctx)
        else:
            input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
            input_data.message = prompt_data.message
            input_data.values = prompt_data.input

    async def __convert_current_value(self, ctx, category, option):
        current_value = await self.bot.values.get_config(ctx, category, option)

        converted_input = await self.bot.values.prepare_input(category, option, str(current_value), ctx)

        if converted_input is not None or True:
            return converted_input
        return current_value

    async def __add_valid_field(self, ctx, prompt, category, option):
        field_value = await self.bot.values.get_valid_input(category, option)
        if field_value is None:
            return prompt

        string = await s.get_string(ctx, s.String("config", "valid_entries"))
        if field_value == "boolean":
            field_value = ["True", "False"]
            field_value = '\n'.join(field_value)
        elif field_value == "channel":
            string = await s.get_string(ctx, s.String("config", "channel_type"))
            field_value = string.string
        elif field_value == "role":
            string = await s.get_string(ctx, s.String("config", "role_type"))
            field_value = string.string
        else:
            field_value = '\n'.join(field_value)

        await prompt.add_field(string.string, field_value, False)
        return prompt

    async def __check_value_data(self, ctx, input_data):
        prepared_input = await self.bot.values.prepare_input(input_data.category, input_data.option, input_data.values, ctx)
        if isinstance(prepared_input, ConfigStatus):
            await self.__show_config_status(ctx, input_data.message, prepared_input)
            return
        status = await self.bot.values.set_config(ctx, input_data.category, input_data.option, prepared_input)
        await self.__show_config_status(ctx, input_data.message, status)

    async def __show_config_status(self, ctx, message, error):
        embed = discord.Embed()

        string_desc = None
        if error == ConfigStatus.OPTION_DOES_NOT_EXIST:
            string = await s.get_string(ctx, s.String("config_status", "OPTION_DOES_NOT_EXIST"))
        elif error == ConfigStatus.CONVERSION_FAILED:
            string = await s.get_string(ctx, s.String("config_status", "CONVERSION_FAILED"))
        elif error == ConfigStatus.NOT_IN_VALID_LIST:
            string = await s.get_string(ctx, s.String("config_status", "NOT_IN_VALID_LIST"))
            string_desc = await s.get_string(ctx, s.String("config_status", "NOT_IN_VALID_LIST_DESC"))
        elif error == ConfigStatus.UNKNOWN_DATA_TYPE:
            string = await s.get_string(ctx, s.String("config_status", "UNKNOWN_DATA_TYPE"))
        elif error == ConfigStatus.NOT_VALID_FOR_DATA_TYPE:
            string = await s.get_string(ctx, s.String("config_status", "NOT_VALID_FOR_DATA_TYPE"))
            string_desc = await s.get_string(ctx, s.String("config_status", "NOT_VALID_FOR_DATA_TYPE_DESC"))
        elif error == ConfigStatus.TEXT_CHANNEL_NOT_FOUND:
            string = await s.get_string(ctx, s.String("config_status", "TEXT_CHANNEL_NOT_FOUND"))
            string_desc = await s.get_string(ctx, s.String("config_status", "TEXT_CHANNEL_NOT_FOUND_DESC"))
        elif error == ConfigStatus.ROLE_NOT_FOUND:
            string = await s.get_string(ctx, s.String("config_status", "ROLE_NOT_FOUND"))
            string_desc = await s.get_string(ctx, s.String("config_status", "ROLE_NOT_FOUND_DESC"))
        elif error == ConfigStatus.SAVE_SUCCESS:
            string = await s.get_string(ctx, s.String("config_status", "SAVE_SUCCESS"))
        elif error == ConfigStatus.SAVE_FAIL:
            string = await s.get_string(ctx, s.String("config_status", "SAVE_FAIL"))
        else:
            string = await s.get_string(ctx, s.String("config_status", "OTHER"))

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
