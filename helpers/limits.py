from dataclasses import dataclass
from enum import Enum

import discord


class LimitStep(Enum):
    NO_INFO = 0
    OUTER_SCOPE = 1
    NAME = 2
    INNER_SCOPE = 3
    CONFIG_TYPE = 4
    EDIT_TYPE = 5
    VALUES = 6
    FINISHED = 7


class OuterScope(Enum):
    CATEGORY = 0
    COMMAND = 1


class InnerScope(Enum):
    ROLE = 0
    CHANNEL = 1


class ConfigType(Enum):
    ENABLED = 0
    WHITELIST = 1
    BLACKLIST = 2


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
    values: list = None
