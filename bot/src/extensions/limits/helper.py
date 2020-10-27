import copy
import shlex
from distutils.util import strtobool
from typing import Union

from discord.ext import commands
from discord.ext.commands import Context

from extensions.limits.dataclasses import PreparedInput, InputData
from extensions.limits.enums import InnerScope, EditType, OuterScope, ConfigType


async def prepare_input(ctx: Context, inner_scope: InnerScope, user_input: Union[str, list], get_name: bool = False) -> PreparedInput:
    """
    Goes through every element and converts it to role or channel.

    Parameters
    ----------
    ctx: Context
        The invocation context
    inner_scope: InnerScope
        The inner scope defining whether role or channel converter will be used
    user_input: Union(str, list)
        String is converted to list using shlex
    get_name: bool, optional
        Sets if returned list should include names instead of IDs

    Returns
    -------
    PreparedInput element
    """
    user_input = await __convert_input_to_list(user_input)

    prepared_input = PreparedInput()

    if len(user_input) == 0:
        prepared_input.successful = False
        return prepared_input

    if inner_scope == InnerScope.ENABLED:
        try:
            prepared_input.list.append(bool(strtobool(user_input[0])))
        except ValueError:
            prepared_input.successful = False
        return prepared_input

    for item in user_input:
        try:
            if inner_scope == InnerScope.ROLE:
                role = await commands.RoleConverter().convert(ctx, item)
                if get_name:
                    prepared_input.list.append(role.name)
                else:
                    prepared_input.list.append(role.id)
            elif inner_scope == InnerScope.CHANNEL:
                channel = await commands.TextChannelConverter().convert(ctx, item)
                if get_name:
                    prepared_input.list.append(channel.name)
                else:
                    prepared_input.list.append(channel.id)
        except commands.CommandError:
            prepared_input.successful = False
            return prepared_input
    return prepared_input


async def set_limit(ctx: Context, input_data: InputData):
    """
    Iterates config dictionaries and sets given limit.

    Parameters
    ----------
    ctx: Context
    input_data: InputData
    """
    ctx.bot.config[str(ctx.guild.id)].setdefault("limits", {})
    outer_scope_str = await get_outer_scope_str(input_data)
    ctx.bot.config[str(ctx.guild.id)]["limits"].setdefault(outer_scope_str, {})
    ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str].setdefault(input_data.name, {})
    if input_data.inner_scope == InnerScope.ENABLED:
        ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name].setdefault("enabled", input_data.prepared_values[0])
        ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name]["enabled"] = input_data.prepared_values[0]
        return
    inner_scope_str = await get_inner_scope_str(input_data)
    ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name].setdefault(inner_scope_str, {})
    config_type_str = await get_config_type_str(input_data)
    current_list = ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name][inner_scope_str].setdefault(config_type_str, [])
    if input_data.edit_type == EditType.ADD:
        for item in input_data.prepared_values:
            if item not in current_list:
                current_list.append(item)
    elif input_data.edit_type == EditType.REMOVE:
        for item in input_data.prepared_values:
            if item in current_list:
                current_list.remove(item)
    elif input_data.edit_type.REPLACE:
        current_list = input_data.prepared_values
    elif input_data.edit_type.RESET:
        current_list = []
    ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name][inner_scope_str][config_type_str] = current_list


async def get_footer_text(ctx: Context, input_data: InputData) -> str:
    """
    Iterates input data and creates text for footer.

    This text shows exactly the command the user needs to run in the future to return to
    this specific point in the limits configuration.

    Parameters
    ----------
    ctx: Context
    input_data: InputData

    Returns
    -------
    Footer string
    """
    prefix = ctx.bot.config[str(ctx.guild.id)]["general"]["command_prefix"]
    footer_text = prefix + ctx.command.name.lower()
    if input_data.outer_scope is not None:
        footer_text += " " + input_data.outer_scope.name.lower()
    else:
        return footer_text
    if input_data.name is not None:
        footer_text += " " + input_data.name.lower()
    else:
        return footer_text
    if input_data.inner_scope is not None:
        footer_text += " " + input_data.inner_scope.name.lower()
    else:
        return footer_text
    if input_data.config_type is not None:
        footer_text += " " + input_data.config_type.name.lower()
    else:
        return footer_text
    if input_data.edit_type is not None:
        footer_text += " " + input_data.edit_type.name.lower()
    return footer_text


async def get_outer_scope_str(input_data: InputData) -> str:
    """
    Returns string to be used to get/set limits value

    Parameters
    ----------
    input_data: InputData
    """
    outer_scope_str = ""
    if input_data.outer_scope == OuterScope.CATEGORY:
        outer_scope_str = "categories"
    elif input_data.outer_scope == OuterScope.COMMAND:
        outer_scope_str = "commands"
    return outer_scope_str


async def get_inner_scope_str(input_data: Union[InputData, InnerScope]) -> str:
    """
    Returns string to be used to get/set limits value

    Parameters
    ----------
    input_data: InputData
    """
    inner_scope_str = ""
    if isinstance(input_data, InputData):
        inner_scope = input_data.inner_scope
    else:
        inner_scope = input_data

    if inner_scope == InnerScope.ENABLED:
        inner_scope_str = "enabled"
    if inner_scope == InnerScope.CHANNEL:
        inner_scope_str = "channels"
    elif inner_scope == InnerScope.ROLE:
        inner_scope_str = "roles"
    return inner_scope_str


async def get_config_type_str(input_data: Union[InputData, ConfigType]):
    """
    Returns string to be used to get/set limits value

    Parameters
    ----------
    input_data: InputData
    """
    config_type_str = ""
    if isinstance(input_data, InputData):
        config_type = input_data.config_type
    else:
        config_type = input_data

    if config_type == ConfigType.WHITELIST:
        config_type_str = "whitelist"
    elif config_type == ConfigType.BLACKLIST:
        config_type_str = "blacklist"
    return config_type_str


async def __convert_input_to_list(user_input) -> list:
    if isinstance(user_input, str):
        user_input = shlex.split(user_input)
    elif isinstance(user_input, bool):
        user_input = [str(user_input)]
    user_input = copy.deepcopy(user_input)
    for i, item in enumerate(user_input):
        if isinstance(item, int):
            user_input[i] = str(item)
    return user_input
