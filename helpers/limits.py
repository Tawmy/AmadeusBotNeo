import shlex
from dataclasses import dataclass, field
from distutils.util import strtobool
from enum import Enum
from typing import Union, List

import discord
from discord.ext import commands
from discord.ext.commands import Context


class LimitStep(Enum):
    NO_INFO = 0
    OUTER_SCOPE = 1
    NAME = 2
    INNER_SCOPE = 3
    CONFIG_TYPE = 4
    EDIT_TYPE = 5
    VALUES = 6
    PREPARED = 7
    FINISHED = 8


class OuterScope(Enum):
    CATEGORY = 0
    COMMAND = 1


class InnerScope(Enum):
    ENABLED = 0
    ROLE = 1
    CHANNEL = 2


class ConfigType(Enum):
    WHITELIST = 0
    BLACKLIST = 1


class EditType(Enum):
    ADD = 0
    REMOVE = 1
    REPLACE = 2
    RESET = 3


@dataclass
class InputData:
    limit_step: LimitStep = LimitStep.NO_INFO
    message: discord.Message = None
    outer_scope: OuterScope = None
    inner_scope: InnerScope = None
    config_type: ConfigType = None
    edit_type: EditType = None
    name: str = None
    values: Union[str, list] = None
    prepared_values: list = None


@dataclass
class PreparedInput:
    successful: bool = True
    list: List = field(default_factory=list)


async def prepare_input(ctx: Context, inner_scope: InnerScope, user_input: Union[str, list]) -> PreparedInput:
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

    Returns
    -------
    PreparedInput element
    """
    if isinstance(user_input, str):
        user_input = shlex.split(user_input)

    prepared_input = PreparedInput()

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
                prepared_input.list.append(role.id)
            elif inner_scope == InnerScope.CHANNEL:
                channel = await commands.TextChannelConverter().convert(ctx, item)
                prepared_input.list.append(channel.id)
        except commands.CommandError:
            prepared_input.successful = False
            return prepared_input
    return prepared_input


async def set_limit(ctx: Context, input_data: InputData) -> bool:
    ctx.bot.config[str(ctx.guild.id)].setdefault("limits", {})
    outer_scope_str = ""
    if input_data.outer_scope == OuterScope.CATEGORY:
        outer_scope_str = "categories"
    elif input_data.outer_scope == OuterScope.COMMAND:
        outer_scope_str = "commands"
    ctx.bot.config[str(ctx.guild.id)]["limits"].setdefault(outer_scope_str, {})
    ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str].setdefault(input_data.name, {})
    inner_scope_str = ""
    if input_data.inner_scope == InnerScope.ENABLED:
        ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name].setdefault("enabled", input_data.prepared_values[0])
        return True
    elif input_data.inner_scope == InnerScope.CHANNEL:
        inner_scope_str = "channels"
    elif input_data.inner_scope == InnerScope.ROLE:
        inner_scope_str = "roles"
    ctx.bot.config[str(ctx.guild.id)]["limits"][outer_scope_str][input_data.name].setdefault(inner_scope_str, {})
    config_type_str = ""
    if input_data.config_type == ConfigType.WHITELIST:
        config_type_str = "whitelist"
    elif input_data.config_type == ConfigType.BLACKLIST:
        config_type_str = "blacklist"
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
    pass

