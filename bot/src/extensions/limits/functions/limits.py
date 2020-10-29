from collections import defaultdict
from typing import Union

import discord
from discord.ext.commands import Context

from components.amadeusMenu import AmadeusMenu, AmadeusMenuStatus, AmadeusMenuResult
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptResult, AmadeusPromptStatus
from extensions.config.helper import save_config
from extensions.limits.dataclasses import InputData, PreparedInput
from extensions.limits.enums import InnerScope, LimitStep, OuterScope, ConfigType, EditType, LimitStatus
from extensions.limits import helper
from helpers import strings as s, general


async def check_input(ctx: Context, args, input_data: InputData) -> InputData:
    outer_scope = await __get_outer_scope(args[0])
    if outer_scope is not None:
        input_data.outer_scope = outer_scope
        if len(args) > 1:
            name = await __get_name(ctx, input_data.outer_scope, args[1])
            if name is not None:
                input_data.name = name
                if len(args) > 2:
                    inner_scope = await __get_inner_scope(args[2])
                    if inner_scope is not None:
                        input_data.inner_scope = inner_scope
                        if len(args) > 3:
                            if input_data.inner_scope == InnerScope.ENABLED:
                                input_data.values = args[3]
                                input_data.limit_step = LimitStep.VALUES
                                return input_data
                            config_type = await __get_config_type(args[3])
                            if config_type is not None:
                                input_data.config_type = config_type
                                if len(args) > 4:
                                    edit_type = await __get_edit_type(args[4])
                                    if edit_type is not None:
                                        input_data.edit_type = edit_type
                                        if len(args) > 5:
                                            input_data.values = args[5:]
                                            input_data.limit_step = LimitStep.VALUES
                                        else:
                                            input_data.limit_step = LimitStep.EDIT_TYPE
                                    else:
                                        input_data.limit_step = LimitStep.CONFIG_TYPE
                                else:
                                    input_data.limit_step = LimitStep.CONFIG_TYPE
                            else:
                                input_data.limit_step = LimitStep.INNER_SCOPE
                        else:
                            if input_data.inner_scope == InnerScope.ENABLED:
                                input_data.limit_step = LimitStep.EDIT_TYPE
                            else:
                                input_data.limit_step = LimitStep.INNER_SCOPE
                    else:
                        input_data.limit_step = LimitStep.NAME
                else:
                    input_data.limit_step = LimitStep.NAME
            else:
                input_data.limit_step = LimitStep.OUTER_SCOPE
        else:
            input_data.limit_step = LimitStep.OUTER_SCOPE
    else:
        input_data.limit_step = LimitStep.NO_INFO
    return input_data


async def collect_limits_data(ctx: Context, input_data: InputData):
    while input_data.limit_step is not LimitStep.FINISHED:
        if input_data.limit_step == LimitStep.NO_INFO:
            await __ask_for_outer_scope(ctx, input_data)
        elif input_data.limit_step == LimitStep.OUTER_SCOPE:
            await __ask_for_name(ctx, input_data)
        elif input_data.limit_step == LimitStep.NAME:
            await __ask_for_inner_scope(ctx, input_data)
        elif input_data.limit_step == LimitStep.INNER_SCOPE:
            await __ask_for_config_type(ctx, input_data)
        elif input_data.limit_step == LimitStep.CONFIG_TYPE:
            await __ask_for_edit_type(ctx, input_data)
        elif input_data.limit_step == LimitStep.EDIT_TYPE and input_data.inner_scope != InnerScope.ENABLED:
            await __ask_for_values(ctx, input_data)
        elif input_data.limit_step == LimitStep.EDIT_TYPE and input_data.inner_scope == InnerScope.ENABLED:
            await __ask_for_enable(ctx, input_data)
        elif input_data.limit_step == LimitStep.VALUES:
            await __process_input(ctx, input_data)
        elif input_data.limit_step == LimitStep.PREPARED:
            await __save_limits(ctx, input_data)


async def __get_outer_scope(user_input: str) -> OuterScope:
    user_input = user_input.lower()
    if user_input in ["command", "cmd"]:
        return OuterScope.COMMAND
    elif user_input in ["category", "cat"]:
        return OuterScope.CATEGORY


async def __get_name(ctx: Context, outer_scope: OuterScope, user_input: str) -> str:
    if outer_scope == OuterScope.CATEGORY:
        for cog in ctx.bot.cogs:
            if user_input.lower() == cog.lower():
                return cog.lower()
    elif outer_scope == OuterScope.COMMAND:
        for command in ctx.bot.commands:
            if user_input.lower() == str(command).lower():
                return str(command).lower()


async def __get_inner_scope(user_input: str) -> InnerScope:
    user_input = user_input.lower()
    if user_input in ["role", "roles"]:
        return InnerScope.ROLE
    elif user_input in ["channel", "channels"]:
        return InnerScope.CHANNEL
    elif user_input in ["enabled", "enable", "on"]:
        return InnerScope.ENABLED


async def __get_config_type(user_input: str) -> ConfigType:
    user_input = user_input.lower()
    if user_input in ["whitelist", "white list", "wl", "allow list", "allowlist", "al"]:
        return ConfigType.WHITELIST
    elif user_input in ["blacklist", "black list", "bl", "deny list", "denylist", "dl"]:
        return ConfigType.BLACKLIST


async def __get_edit_type(user_input: str) -> EditType:
    user_input = user_input.lower()
    if user_input in ["add", "append"]:
        return EditType.ADD
    elif user_input == "remove":
        return EditType.REMOVE
    elif user_input == "replace":
        return EditType.REPLACE
    elif user_input in ["reset", "default", "revert"]:
        return EditType.RESET


async def __ask_for_outer_scope(ctx: Context, input_data: InputData):
    string = await s.get_string("limits", "select_outer_scope", ctx)
    menu = AmadeusMenu(ctx.bot, string.string)
    await menu.set_user_specific(True)

    string = await s.get_string("limits", "category", ctx)
    string_desc = await s.get_string("limits", "category_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    string = await s.get_string("limits", "command", ctx)
    string_desc = await s.get_string("limits", "command_desc", ctx)
    await menu.add_option(string.string, string_desc.string)

    menu_data = await __show_menu_and_check_result(ctx, menu, input_data)
    if menu_data.status == AmadeusMenuStatus.SELECTED:
        input_data.limit_step = LimitStep.OUTER_SCOPE
        input_data.message = menu_data.message
        if menu_data.reaction_index == 0:
            input_data.outer_scope = OuterScope.CATEGORY
        elif menu_data.reaction_index == 1:
            input_data.outer_scope = OuterScope.COMMAND


async def __ask_for_name(ctx: Context, input_data: InputData):
    if input_data.outer_scope == OuterScope.CATEGORY:
        req_title = "category"
        req_description = "input_category"
    else:
        req_title = "command"
        req_description = "input_command"
    string_title = await s.get_string("limits", req_title, ctx)
    string_description = await s.get_string("limits", req_description, ctx)

    prompt = AmadeusPrompt(ctx.bot, string_title.string)
    await prompt.set_description(string_description.string)
    await prompt.set_user_specific(True)
    await __add_name_prompt_details(ctx, input_data.outer_scope, prompt)

    prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)

    if await __check_prompt_result(ctx, prompt, prompt_data, input_data):
        name = await __get_name(ctx, input_data.outer_scope, prompt_data.input)
        if name is not None:
            input_data.limit_step = LimitStep.NAME
            input_data.message = prompt_data.message
            input_data.name = name
        else:
            await __show_limit_status(ctx, input_data, LimitStatus.NAME_NOT_FOUND)


async def __add_name_prompt_details(ctx: Context, outer_scope: OuterScope, prompt: AmadeusPrompt):
    cog_list = []
    for cog in ctx.bot.cogs:
        cog_list.append(cog.lower())
    if outer_scope == OuterScope.CATEGORY:
        cog_list_str = "\n".join(cog_list)
        string = await s.get_string("limits", "categories", ctx)
        await prompt.add_field(string.string, cog_list_str)
    if outer_scope == OuterScope.COMMAND:
        cog_with_commands_dict = defaultdict(list)
        for command in ctx.bot.commands:
            if command.cog_name is not None and command.name not in ctx.bot.config["bot"]["limits"]["no_limits"]:
                cog_with_commands_dict[command.cog_name.lower()].append(command.name.lower())
        for cog_name, commands_list in cog_with_commands_dict.items():
            commands_str = "\n".join(commands_list)
            await prompt.add_field(cog_name, commands_str)


async def __ask_for_inner_scope(ctx: Context, input_data: InputData):
    title = await __get_menu_title(ctx, input_data)
    menu = AmadeusMenu(ctx.bot, title)
    await menu.set_user_specific(True)
    string = await s.get_string("limits", "enabled", ctx)
    string_desc = await s.get_string("limits", "enabled_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    string = await s.get_string("limits", "role_s", ctx)
    string_desc = await s.get_string("limits", "role_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    if input_data.outer_scope != OuterScope.CATEGORY:
        string = await s.get_string("limits", "channel_s", ctx)
        string_desc = await s.get_string("limits", "channel_desc", ctx)
        await menu.add_option(string.string, string_desc.string)
    await __add_current_values(ctx, input_data, menu)

    menu_data = await __show_menu_and_check_result(ctx, menu, input_data)
    if menu_data.status == AmadeusMenuStatus.SELECTED:
        input_data.message = menu_data.message
        if menu_data.reaction_index == 0:
            input_data.inner_scope = InnerScope.ENABLED
            input_data.limit_step = LimitStep.EDIT_TYPE
        else:
            input_data.limit_step = LimitStep.INNER_SCOPE
        if menu_data.reaction_index == 1:
            input_data.inner_scope = InnerScope.ROLE
        elif menu_data.reaction_index == 2:
            input_data.inner_scope = InnerScope.CHANNEL


async def __ask_for_config_type(ctx: Context, input_data: InputData):
    title = await __get_menu_title(ctx, input_data)
    menu = AmadeusMenu(ctx.bot, title)
    await menu.set_user_specific(True)

    string = await s.get_string("limits", "whitelist", ctx)
    req_desc = ""
    if input_data.inner_scope == InnerScope.ROLE:
        req_desc = "whitelist_desc_role"
    elif input_data.inner_scope == InnerScope.CHANNEL:
        req_desc = "whitelist_desc_channel"
    # TODO if req_desc = "" causes exception
    string_desc = await s.get_string("limits", req_desc, ctx)
    await menu.add_option(string.string, string_desc.string)

    string = await s.get_string("limits", "blacklist", ctx)
    req_desc = ""
    if input_data.inner_scope == InnerScope.ROLE:
        req_desc = "blacklist_desc_role"
    elif input_data.inner_scope == InnerScope.CHANNEL:
        req_desc = "blacklist_desc_channel"
    # TODO if req_desc = "" causes exception
    string_desc = await s.get_string("limits", req_desc, ctx)
    await menu.add_option(string.string, string_desc.string)

    await __add_current_values(ctx, input_data, menu)

    menu_data = await __show_menu_and_check_result(ctx, menu, input_data)
    if menu_data.status == AmadeusMenuStatus.SELECTED:
        input_data.limit_step = LimitStep.CONFIG_TYPE
        input_data.message = menu_data.message
        if menu_data.reaction_index == 0:
            input_data.config_type = ConfigType.WHITELIST
        elif menu_data.reaction_index == 1:
            input_data.config_type = ConfigType.BLACKLIST


async def __ask_for_edit_type(ctx: Context, input_data):
    title = await __get_menu_title(ctx, input_data)

    menu = AmadeusMenu(ctx.bot, title)
    await menu.set_user_specific(True)

    await __add_current_values(ctx, input_data, menu)

    string = await s.get_string("limits", "add", ctx)
    string_desc = await s.get_string("limits", "add_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    string = await s.get_string("limits", "remove", ctx)
    string_desc = await s.get_string("limits", "remove_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    string = await s.get_string("limits", "replace", ctx)
    string_desc = await s.get_string("limits", "replace_desc", ctx)
    await menu.add_option(string.string, string_desc.string)
    string = await s.get_string("limits", "reset", ctx)
    string_desc = await s.get_string("limits", "reset_desc", ctx)
    await menu.add_option(string.string, string_desc.string)

    menu_data = await __show_menu_and_check_result(ctx, menu, input_data)
    if menu_data.status == AmadeusMenuStatus.SELECTED:
        input_data.limit_step = LimitStep.EDIT_TYPE
        input_data.message = menu_data.message
        if menu_data.reaction_index == 0:
            input_data.edit_type = EditType.ADD
        elif menu_data.reaction_index == 1:
            input_data.edit_type = EditType.REMOVE
        elif menu_data.reaction_index == 2:
            input_data.edit_type = EditType.REPLACE
        elif menu_data.reaction_index == 3:
            input_data.edit_type = EditType.RESET


async def __ask_for_enable(ctx: Context, input_data: InputData):
    title = await __get_menu_title(ctx, input_data)
    menu = AmadeusMenu(ctx.bot, title)
    await menu.set_user_specific(True)

    string = await s.get_string("limits", "enable", ctx)
    await menu.add_option(string.string)
    string = await s.get_string("limits", "disable", ctx)
    await menu.add_option(string.string)

    menu_data = await __show_menu_and_check_result(ctx, menu, input_data)
    if menu_data.status == AmadeusMenuStatus.SELECTED:
        input_data.message = menu_data.message
        if menu_data.reaction_index == 0:
            input_data.values = "true"
        elif menu_data.reaction_index == 1:
            input_data.values = "false"
        input_data.limit_step = LimitStep.VALUES


async def __ask_for_values(ctx: Context, input_data: InputData):
    title = await __get_menu_title(ctx, input_data)
    prompt = AmadeusPrompt(ctx.bot, title)
    desc_string = None
    if input_data.edit_type == EditType.ADD:
        desc_string = await s.get_string("limits", "add_desc", ctx)
    elif input_data.edit_type == EditType.REMOVE:
        desc_string = await s.get_string("limits", "remove_desc", ctx)
    elif input_data.edit_type == EditType.REPLACE:
        desc_string = await s.get_string("limits", "replace_desc", ctx)
    elif input_data.edit_type == EditType.RESET:
        desc_string = await s.get_string("limits", "reset_desc", ctx)
    if desc_string is not None:
        await prompt.set_description(desc_string.string)

    await __add_current_values(ctx, input_data, prompt)

    prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)
    if await __check_prompt_result(ctx, prompt, prompt_data, input_data):
        input_data.message = prompt_data.message
        input_data.values = prompt_data.input
        input_data.limit_step = LimitStep.VALUES


async def __process_input(ctx: Context, input_data: InputData):
    prepared_input = await helper.prepare_input(ctx, input_data.inner_scope, input_data.values)
    if prepared_input.successful:
        input_data.prepared_values = prepared_input.list
        input_data.limit_step = LimitStep.PREPARED
    else:
        if input_data.inner_scope == InnerScope.ROLE:
            await __show_limit_status(ctx, input_data, LimitStatus.ROLE_NOT_FOUND)
        elif input_data.inner_scope == InnerScope.CHANNEL:
            await __show_limit_status(ctx, input_data, LimitStatus.TEXT_CHANNEL_NOT_FOUND)


async def __save_limits(ctx: Context, input_data: InputData):
    await helper.set_limit(ctx, input_data)
    if await save_config(ctx.bot, ctx.guild.id):
        await __show_limit_status(ctx, input_data, LimitStatus.SAVE_SUCCESS)
    else:
        await __show_limit_status(ctx, input_data, LimitStatus.SAVE_FAIL)


async def __get_menu_title(ctx: Context, input_data: InputData) -> str:
    outer_scope_str = await s.get_string("limits", input_data.outer_scope.name.lower(), ctx)
    return input_data.name.capitalize() + " " + outer_scope_str.string


async def __add_edit_type_to_title(ctx: Context, input_data: InputData) -> str:
    if input_data.edit_type is not None:
        edit_type = None
        if input_data.edit_type == EditType.ADD:
            edit_type = "add_to"
        elif input_data.edit_type == EditType.REMOVE:
            edit_type = "remove_from"
        elif input_data.edit_type == EditType.REPLACE:
            edit_type = "replace_list"
        elif input_data.edit_type == EditType.RESET:
            edit_type = "reset_list"
        if edit_type is not None:
            string = await s.get_string("limits", edit_type, ctx)
            return string.string if string is not None else ""
    return ""


async def __add_inner_scope_to_title(ctx: Context, input_data: InputData) -> str:
    inner_scope_str = None
    if input_data.inner_scope == InnerScope.ROLE:
        inner_scope_str = await s.get_string("limits", "role", ctx)
    elif input_data.inner_scope == InnerScope.CHANNEL:
        inner_scope_str = await s.get_string("limits", "channel", ctx)
    if inner_scope_str is not None:
        return inner_scope_str.string
    else:
        await __show_limit_status(ctx, input_data, LimitStatus.OTHER)


async def __add_config_type_to_title(ctx: Context, input_data: InputData) -> str:
    config_type_str = None
    if input_data.config_type == ConfigType.WHITELIST:
        config_type_str = await s.get_string("limits", "whitelist", ctx)
    elif input_data.config_type == ConfigType.BLACKLIST:
        config_type_str = await s.get_string("limits", "blacklist", ctx)
    if config_type_str is not None:
        return " " + config_type_str.string
    else:
        await __show_limit_status(ctx, input_data, LimitStatus.OTHER)


async def __add_outer_scope_to_title(ctx: Context, input_data: InputData) -> str:
    outer_scope_str = None
    if input_data.outer_scope == OuterScope.CATEGORY:
        outer_scope_str = await s.get_string("limits", "category", ctx)
    elif input_data.outer_scope == OuterScope.COMMAND:
        outer_scope_str = await s.get_string("limits", "command", ctx)
    if outer_scope_str is not None:
        return " " + outer_scope_str.string
    else:
        await __show_limit_status(ctx, input_data, LimitStatus.OTHER)


async def __show_limit_status(ctx: Context, input_data: InputData, status: LimitStatus):
    input_data.limit_step = LimitStep.FINISHED
    embed = discord.Embed()
    string_desc = None
    if status == LimitStatus.NAME_NOT_FOUND:
        string = await s.get_string("limits_status", "NAME_NOT_FOUND", ctx)
        if input_data.outer_scope == OuterScope.CATEGORY:
            string_desc = await s.get_string("limits_status", "NAME_NOT_FOUND_DESC_CATEGORY", ctx)
        elif input_data.outer_scope == OuterScope.COMMAND:
            string_desc = await s.get_string("limits_status", "NAME_NOT_FOUND_DESC_COMMAND", ctx)
    elif status == LimitStatus.TEXT_CHANNEL_NOT_FOUND:
        string = await s.get_string("config_status", "TEXT_CHANNEL_NOT_FOUND", ctx)
        string_desc = await s.get_string("config_status", "TEXT_CHANNEL_NOT_FOUND_DESC", ctx)
    elif status == LimitStatus.ROLE_NOT_FOUND:
        string = await s.get_string("config_status", "ROLE_NOT_FOUND", ctx)
        string_desc = await s.get_string("config_status", "ROLE_NOT_FOUND_DESC", ctx)
    elif status == LimitStatus.SAVE_SUCCESS:
        string = await s.get_string("limits_status", "SAVE_SUCCESS", ctx)
    else:
        string = await s.get_string("config_status", "OTHER", ctx)
    embed.title = string.string
    if string_desc is not None and string_desc.successful:
        embed.description = string_desc.string

    # TODO this needs to be more dynamic, like set_footer in amadeusMenu
    # it works for now because config is always user specific
    name = ctx.author.display_name
    avatar = ctx.author.avatar_url_as(static_format="png")
    embed.set_footer(text=name, icon_url=avatar)

    if input_data.message is not None:
        await input_data.message.edit(embed=embed)
    else:
        await ctx.send(embed=embed)


async def __add_current_values(ctx: Context, input_data: InputData, menu: Union[AmadeusMenu, AmadeusPrompt]):
    if await __check_field_enabled(input_data):
        await __add_field_to_menu(ctx, input_data, menu, InnerScope.ENABLED)
    if await __check_field_channel_whitelist(input_data):
        await __add_field_to_menu(ctx, input_data, menu, InnerScope.CHANNEL, ConfigType.WHITELIST)
    if await __check_field_channel_blacklist(input_data):
        await __add_field_to_menu(ctx, input_data, menu, InnerScope.CHANNEL, ConfigType.BLACKLIST)
    if await __check_field_role_whitelist(input_data):
        await __add_field_to_menu(ctx, input_data, menu, InnerScope.ROLE, ConfigType.WHITELIST)
    if await __check_field_role_blacklist(input_data):
        await __add_field_to_menu(ctx, input_data, menu, InnerScope.ROLE, ConfigType.BLACKLIST)


async def __check_field_enabled(input_data: InputData) -> bool:
    return input_data.config_type is None and input_data.inner_scope is None \
           or input_data.inner_scope == InnerScope.ENABLED


async def __check_field_channel_whitelist(input_data: InputData) -> bool:
    return input_data.config_type is None and input_data.inner_scope is None \
           or input_data.config_type is None and input_data.inner_scope == InnerScope.CHANNEL \
           or input_data.inner_scope == InnerScope.CHANNEL and input_data.config_type == ConfigType.WHITELIST


async def __check_field_channel_blacklist(input_data: InputData) -> bool:
    return input_data.config_type is None and input_data.inner_scope is None \
           or input_data.config_type is None and input_data.inner_scope == InnerScope.CHANNEL \
           or input_data.inner_scope == InnerScope.CHANNEL and input_data.config_type == ConfigType.BLACKLIST


async def __check_field_role_whitelist(input_data: InputData) -> bool:
    return input_data.config_type is None and input_data.inner_scope is None \
           or input_data.config_type is None and input_data.inner_scope == InnerScope.ROLE \
           or input_data.inner_scope == InnerScope.ROLE and input_data.config_type == ConfigType.WHITELIST


async def __check_field_role_blacklist(input_data: InputData) -> bool:
    return input_data.config_type is None and input_data.inner_scope is None \
           or input_data.config_type is None and input_data.inner_scope == InnerScope.ROLE \
           or input_data.inner_scope == InnerScope.ROLE and input_data.config_type == ConfigType.BLACKLIST


async def __add_field_to_menu(ctx: Context, input_data: InputData, menu: AmadeusMenu, inner_scope: InnerScope,
                              config_type: ConfigType = None):
    inner_scope_str = await s.get_string("limits", inner_scope.name.lower(), ctx)
    if inner_scope == InnerScope.ENABLED:
        title = inner_scope_str.string.capitalize()
    else:
        if config_type is None:
            return
        config_type_str = await s.get_string("limits", config_type.name.lower(), ctx)
        title = inner_scope_str.string.capitalize() + " " + config_type_str.string.capitalize()
    limit_list = await __get_list(ctx, input_data, inner_scope, config_type)
    prepared_input = await helper.prepare_input(ctx, inner_scope, limit_list, True)
    limit_list_str = await __get_limit_string(prepared_input, inner_scope)
    await menu.add_field(title, limit_list_str)


async def __get_limit_string(prepared_input: PreparedInput, inner_scope: InnerScope) -> str:
    if len(prepared_input.list) > 0:
        return '\n'.join([str(element) for element in prepared_input.list])
    elif inner_scope == InnerScope.ENABLED and len(prepared_input.list) == 0:
        return "True"
    else:
        return "-"


async def __get_list(ctx: Context, input_data: InputData, inner_scope: InnerScope,
                     config_type: ConfigType) -> list:
    outer_scope_str = await helper.get_outer_scope_str(input_data)
    inner_scope_str = await helper.get_inner_scope_str(inner_scope)
    config_type_str = await helper.get_config_type_str(config_type)
    if inner_scope == InnerScope.ENABLED:
        return await general.deep_get_type(list, ctx.bot.config, str(ctx.guild.id), "limits", outer_scope_str,
                                           input_data.name.lower(), inner_scope_str)
    else:
        return await general.deep_get_type(list, ctx.bot.config, str(ctx.guild.id), "limits", outer_scope_str,
                                           input_data.name.lower(), inner_scope_str, config_type_str)


async def __show_menu_and_check_result(ctx: Context, menu: AmadeusMenu,
                                       input_data: InputData) -> AmadeusMenuResult:
    await menu.set_footer_text(await helper.get_footer_text(ctx, input_data))
    menu_data = await menu.show_menu(ctx, 120, input_data.message)
    if menu_data.status != AmadeusMenuStatus.SELECTED:
        input_data.limit_step = LimitStep.FINISHED
        await menu.show_result(ctx)
    return menu_data


async def __check_prompt_result(ctx: Context, prompt: AmadeusPrompt, prompt_data: AmadeusPromptResult,
                                input_data: InputData) -> bool:
    if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
        input_data.limit_step = LimitStep.FINISHED
        await prompt.show_result(ctx)
        return False
    return True