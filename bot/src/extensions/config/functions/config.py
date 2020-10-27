from typing import Union, Any

import discord
from discord.ext.commands import Context

from components import amadeusMenu, amadeusPrompt
from components.amadeusMenu import AmadeusMenuStatus, AmadeusMenu
from components.amadeusPrompt import AmadeusPromptStatus, AmadeusPrompt
from extensions.config import helper
from helpers import strings as s, general
from extensions.config.dataclasses import ConfigStep, InputData, InputType, ConfigStatus


async def check_input(ctx: Context, args: tuple, input_data: InputData) -> InputData:
    category = await __get_category(ctx, args[0])
    if category is not None:
        input_data.category = category
        if len(args) > 1:
            category, option = await __get_option(ctx, args[1], category)
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
        category, option = await __get_option(ctx, args[0], category)
        if option is not None:
            input_data.category = category
            input_data.option = option
            if len(args) > 1:
                input_data.values = args[1:]
                input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
            else:
                input_data.configStep = ConfigStep.OPTION
    return input_data


async def collect_config_data(ctx: Context, input_data: InputData):
    while input_data.configStep is not ConfigStep.FINISHED:
        if input_data.configStep == ConfigStep.NO_INFO:
            await __ask_for_category(ctx, input_data)
        elif input_data.configStep == ConfigStep.CATEGORY:
            await __ask_for_option(ctx, input_data)
        elif input_data.configStep in [ConfigStep.OPTION, ConfigStep.CATEGORY_OPTION]:
            await __show_info(ctx, input_data)
        elif input_data.configStep == ConfigStep.CATEGORY_OPTION_CONFIRMED:
            await __ask_for_value(ctx, input_data)
        elif input_data.configStep == ConfigStep.CATEGORY_OPTION_SETDEFAULT:
            await __set_default_value(ctx, input_data)
            return
        elif input_data.configStep in [ConfigStep.CATEGORY_OPTION_VALUE, ConfigStep.CATEGORY_OPTION_CANCELLED]:
            return


async def __ask_for_category(ctx: Context, input_data: InputData):
    string = await s.get_string(ctx, "config", "select_category")
    menu = amadeusMenu.AmadeusMenu(ctx.bot, string.string)
    await menu.set_user_specific(True)
    category_names = []
    for category_key, category_val in ctx.bot.values["options"].items():
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


async def __get_category(ctx: Context, user_input: str) -> Union[None, str]:
    user_input = user_input.lower()
    if await general.deep_get(ctx.bot.values["options"], user_input) is not None:
        return user_input
    else:
        for category_key, category_val in ctx.bot.values["options"].items():
            if await __check_value(ctx, category_val, user_input) is True:
                return category_key
    return None


async def __get_option(ctx: Context, user_input: str, category: str = None) -> tuple:
    user_input = user_input.lower()
    if category is not None and await general.deep_get(ctx.bot.values["options"], category, "list",
                                                       user_input) is not None:
        return category, user_input

    for category_key, category_val in ctx.bot.values["options"].items():
        for option_key, option_val in category_val.get("list").items():
            if await __check_value(ctx, option_val, user_input) is True:
                return category_key, option_key
    return None, None


async def __check_value(ctx: Context, value: dict, user_input: str) -> bool:
    # check for value name in server language
    lang = await s.get_guild_language(ctx)
    option = await general.deep_get(value, "name", lang)
    if option is not None and user_input == option.lower():
        return True
    elif lang != ctx.bot.default_language:
        # if value does not have a name in specified language, check against default language
        option = await general.deep_get(value, "name", ctx.bot.default_language)
        if option is not None and user_input == option.lower():
            return True
    return False


async def __ask_for_option(ctx: Context, input_data: InputData):
    # prepare menu
    category = await general.deep_get(ctx.bot.values["options"], input_data.category)
    category_values = await s.extract_config_option_strings(ctx, category)
    menu = amadeusMenu.AmadeusMenu(ctx.bot, category_values.name)
    await menu.set_description(category_values.description)
    await menu.set_user_specific(True)

    await __add_footer(ctx, input_data, menu)

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


async def __show_info(ctx: Context, input_data: InputData):
    # prepare menu
    option_full = await general.deep_get(ctx.bot.values["options"], input_data.category, "list", input_data.option)
    option_values = await s.extract_config_option_strings(ctx, option_full)
    menu = amadeusMenu.AmadeusMenu(ctx.bot, option_values.name)
    await menu.set_description(option_values.description)
    await menu.set_user_specific(True)

    await __add_footer(ctx, input_data, menu)

    await __add_info_fields_to_info(ctx, input_data, menu, option_full)
    await __add_options_to_info(ctx, menu, option_full)

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


async def __add_info_fields_to_info(ctx: Context, input_data: InputData, menu: AmadeusMenu, option_full: dict):
    # add fields to menu
    current_value = await __convert_current_value(ctx, input_data.category, input_data.option)

    string = await s.get_string(ctx, "config", "current_value")
    await menu.add_field(string.string, current_value)

    string = await s.get_string(ctx, "config", "default_value")
    default_value = await general.deep_get(option_full, "default")
    if default_value is not None:
        await menu.add_field(string.string, default_value)

    # TODO add field about is_list

    await __add_valid_field(ctx, menu, input_data.category, input_data.option)


async def __add_options_to_info(ctx: Context, menu: AmadeusMenu, option_full: dict):
    string = await s.get_string(ctx, "config", "option_change")
    await menu.add_option(string.string)
    default_value = await general.deep_get(option_full, "default")
    if default_value is not None:
        string = await s.get_string(ctx, "config", "option_setdefault")
        await menu.add_option(string.string)


async def __add_footer(ctx: Context, input_data: InputData, menu: AmadeusMenu):
    prefix = ctx.bot.config[str(ctx.guild.id)]["general"]["command_prefix"]
    footer_text = prefix + ctx.command.name + " " + input_data.category
    if input_data.option is not None:
        footer_text = footer_text + " " + input_data.option
    await menu.set_footer_text(footer_text)


async def __ask_for_value(ctx: Context, input_data: InputData):
    option_full = await general.deep_get(ctx.bot.values["options"], input_data.category, "list", input_data.option)
    option_values = await s.extract_config_option_strings(ctx, option_full)
    prompt = amadeusPrompt.AmadeusPrompt(ctx.bot, option_values.name)
    await prompt.set_user_specific(True)
    string = await s.get_string(ctx, "prompt", "please_enter")
    await prompt.set_author(string.string)

    await __add_valid_field(ctx, prompt, input_data.category, input_data.option)

    prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)
    if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
        input_data.configStep = ConfigStep.FINISHED
        await prompt.show_result(ctx)
    else:
        input_data.configStep = ConfigStep.CATEGORY_OPTION_VALUE
        input_data.message = prompt_data.message
        input_data.values = prompt_data.input


async def __set_default_value(ctx: Context, input_data: InputData):
    prepared_input = await helper.set_default_config(ctx, input_data.category, input_data.option)
    await __show_config_status(ctx, input_data.message, prepared_input.status)


async def __convert_current_value(ctx: Context, category: str, option: str) -> Any:
    current_value = await helper.get_config(ctx, category, option)
    converted_input = await helper.prepare_input(ctx, category, option, current_value.value)
    if len(converted_input.list) == 1:
        return converted_input.list[0]
    return converted_input.list


async def __add_valid_field(ctx: Context, menu: Union[AmadeusMenu, AmadeusPrompt], category: str,
                            option: str) -> AmadeusMenu:
    valid_input = await helper.get_valid_input(ctx, category, option)

    if valid_input.input_type == InputType.ANY:
        return menu

    title = await s.get_string(ctx, "config", "valid_entries")
    for i, item in enumerate(valid_input.valid_list):
        if not isinstance(item, str):
            valid_input.valid_list[i] = str(item)
    value = '\n'.join(valid_input.valid_list)
    await menu.add_field(title.string, value, False)
    return menu


async def check_value_data(ctx: Context, input_data: InputData):
    prepared_input = await helper.prepare_input(ctx, input_data.category, input_data.option, input_data.values)
    # if isinstance(prepared_input, ConfigStatus):
    if prepared_input.status != ConfigStatus.PREPARATION_SUCCESSFUL:
        await __show_config_status(ctx, input_data.message, prepared_input.status)
        return
    await helper.set_config(ctx, prepared_input)
    await __show_config_status(ctx, input_data.message, prepared_input.status)


async def __show_config_status(ctx: Context, message: discord.Message, status: ConfigStatus):
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