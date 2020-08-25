import shutil
from os.path import isfile

import discord
from discord.ext.commands import Context

from components.amadeusMenu import AmadeusMenu, AmadeusMenuStatus
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptStatus
from extensions.config.enums import ConfigStatus
from extensions.limits.dataclasses import InputData
from extensions.limits.enums import OuterScope, EditType, InnerScope, ConfigType
from extensions.setup.dataclasses import SetupTypeSelection, UserInput
from extensions.setup.enums import SetupType, InputType, SetupStatus
from helpers import strings as s, general
from extensions.config import helper as c
from extensions.limits import helper as limits


async def prepare_setup_type_selection_menu(ctx: Context, setup_emoji: list) -> AmadeusMenu:
    string = await s.get_string(ctx, "setup", "setup_title")
    string_combination = await s.insert_into_string([ctx.bot.app_info.name], [string.string], s.InsertPosition.LEFT)
    title = string_combination.string_combined

    string = await s.get_string(ctx, "setup", "setup_introduction")
    string_combination = await s.insert_into_string([ctx.bot.app_info.name, ctx.bot.app_info.name], string.list)
    description = string_combination.string_combined

    # Different prompt if server has been configured before
    # Backup current config to subdirectory
    json_file = str(ctx.guild.id) + '.json'
    if isfile('config/' + json_file):
        shutil.copy('config/' + json_file, 'config/backup/' + json_file)
        string = await s.get_string(ctx, "setup", "server_configured_before")
        description += string.string
        emoji = [setup_emoji[1], setup_emoji[2]]
    else:
        string = await s.get_string(ctx, "setup", "setup_confirm_ready")
        description += string.string
        emoji = [setup_emoji[0]]

    menu = AmadeusMenu(ctx.bot, title)
    await menu.set_description(description)
    await menu.append_emoji(emoji)
    return menu


async def ask_for_setup_type(ctx: Context, menu: AmadeusMenu, setup_emoji: list) -> SetupTypeSelection:
    result = await menu.show_menu(ctx, 120)
    setup_type_selection = SetupTypeSelection(result.message)
    if result.status == AmadeusMenuStatus.SELECTED:
        if result.reaction_emoji in [setup_emoji[0], setup_emoji[1]]:
            setup_type_selection.setup_type = SetupType.REGULAR
        elif result.reaction_emoji == setup_emoji[2]:
            setup_type_selection.setup_type = SetupType.FULL_RESET
    else:
        setup_type_selection.setup_type = SetupType.CANCELLED
    return setup_type_selection


async def initialise_guild_config(ctx: Context, setup_type: SetupType):
    # delete config if reset emoji clicked
    if setup_type == SetupType.FULL_RESET:
        ctx.bot.config[str(ctx.guild.id)] = {}
    else:
        ctx.bot.config.setdefault(str(ctx.guild.id), {})


async def iterate_config_options(ctx: Context, setup_user: discord.User, message: discord.Message) -> bool:
    # Iterate categories
    for category_key in ctx.bot.values["options"]:
        # Iterate options in category
        for option_key, option_values in ctx.bot.values["options"][category_key]["list"].items():
            if option_values["is_essential"]:
                user_input = await __ask_for_value(ctx, category_key, option_key, option_values, setup_user, message)
                if user_input.type == InputType.CANCELLED:
                    return False
                await c.set_config(ctx, user_input.prepared_input, False)
    return True


async def __ask_for_value(ctx: Context, c_key: str, o_key: str, o_val: dict, setup_user: discord.User, message: discord.Message) -> UserInput:
    user_input = UserInput()

    option_strings = await s.extract_config_option_strings(ctx, o_val)
    prompt = AmadeusPrompt(ctx.bot, option_strings.name)
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


async def add_default_limits(ctx: Context):
    input_data = InputData(outer_scope=OuterScope.CATEGORY, edit_type=EditType.REPLACE)
    for name_key, name_val in ctx.bot.values["limits"].get("defaults").items():
        input_data.name = name_key
        for inner_scope_key, inner_scope_val in name_val.items():
            if inner_scope_key == "roles":
                input_data.inner_scope = InnerScope.ROLE
            elif inner_scope_key == "channels":
                input_data.inner_scope = InnerScope.CHANNEL
            for edit_type_key, edit_type_val in inner_scope_val.items():
                if edit_type_key == "whitelist":
                    input_data.config_type = ConfigType.WHITELIST
                elif edit_type_key == "blacklist":
                    input_data.config_type = ConfigType.BLACKLIST
                input_data.values = edit_type_val
                await __convert_default_limit(ctx, input_data)
                await limits.set_limit(ctx, input_data)


async def __convert_default_limit(ctx: Context, input_data: InputData):
    element_list = []
    if input_data.inner_scope == InnerScope.ROLE:
        for element in input_data.values:
            element_list.append(await general.deep_get(ctx.bot.config, str(ctx.guild.id), "essential_roles", element))
    elif input_data.inner_scope == InnerScope.CHANNEL:
        for element in input_data.values:
            element_list.append(
                await general.deep_get(ctx.bot.config, str(ctx.guild.id), "essential_channels", element))
    # TODO check if this can throw exception if element is actually None
    prepared_values = await limits.prepare_input(ctx, input_data.inner_scope, element_list)
    if prepared_values.successful:
        input_data.prepared_values = prepared_values.list


async def prepare_status_embed(ctx: Context, setup_status: SetupStatus) -> discord.Embed:
    embed = discord.Embed()
    if setup_status == SetupStatus.SUCCESSFUL:
        string = await s.get_string(ctx, "setup", "setup_successful")
        embed.title = string.string
        string = await s.get_string(ctx, "setup", "setup_successful_description")
        string_combination = await s.insert_into_string([ctx.bot.app_info.name], string.list)
        embed.description = string_combination.string_combined
    elif setup_status == SetupStatus.SAVE_FAILED:
        string = await s.get_string(ctx, "setup", "setup_error_save_config")
        embed.title = string.string
    elif setup_status == SetupStatus.CANCELLED:
        string = await s.get_string(ctx, "setup", "setup_cancelled")
        embed.title = string.string
    return embed


async def check_bot_permissions(ctx: Context, embed: discord.Embed) -> discord.Embed:
    for ch_key, ch_val in ctx.bot.config[str(ctx.guild.id)]["essential_channels"].items():
        channel = ctx.guild.get_channel(ch_val)
        permissions_have = channel.permissions_for(ctx.guild.me)
        permissions_need = ctx.bot.values["options"]["essential_channels"]["list"][ch_key]["permissions"]
        permissions_embed = ""
        for permission in permissions_need:
            if getattr(permissions_have, permission) is True:
                permissions_embed += "✅ " + permission + "\n"
            else:
                permissions_embed += "❌ " + permission + "\n"
        if len(permissions_embed) > 0:
            embed.add_field(name="#" + str(channel), value=permissions_embed)
    return embed


async def add_default_limits_to_embed(ctx: Context, embed: discord.Embed) -> discord.Embed:
    title = "\u200b"
    description_string = await s.get_string(ctx, "setup", "default_limits_description")
    description = description_string.string + "\n"
    for name_key in ctx.bot.values["limits"].get("defaults"):
        description += "• " + name_key + "\n"
    description_string_note = await s.get_string(ctx, "setup", "default_limits_note")
    prefix = ctx.bot.config[str(ctx.guild.id)]["general"]["command_prefix"]
    description_note_command = "`" + prefix + "limits`"
    inserted_string = await s.insert_into_string([description_note_command], description_string_note.list)
    description += "\n" + inserted_string.string_combined
    embed.add_field(name=title, value=description, inline=False)
    return embed


async def set_bot_enabled(ctx: Context):
    prepared_input = await c.prepare_input(ctx, "general", "enabled", True)
    if str(ctx.guild.id) in ctx.bot.corrupt_configs:
        ctx.bot.corrupt_configs.remove(str(ctx.guild.id))
    await c.set_config(ctx, prepared_input, False)
