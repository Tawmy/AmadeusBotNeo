from dataclasses import dataclass, field
from typing import Union, List

import discord

from extensions.limits.enums import LimitStep, OuterScope, InnerScope, ConfigType, EditType


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
