from dataclasses import dataclass
from typing import Union

import discord

from extensions.config.enums import ConfigStep, ReturnType, Datatype, InputType, ConfigStatus, SetupType, SetupInputType


@dataclass
class InputData:
    configStep: ConfigStep = ConfigStep.NO_INFO
    message: discord.message = None
    category: str = None
    option: str = None
    values: list = None


@dataclass
class Config:
    category: str
    name: str
    value: Union[str, int] = None
    return_type: ReturnType = None


@dataclass
class ValidInput:
    datatype: Datatype = None
    valid_list: list = None
    input_type: InputType = InputType.AS_DATATYPE


@dataclass
class PreparedInput:
    category: str
    name: str
    list: list = None
    status: ConfigStatus = None


@dataclass
class SetupTypeSelection:
    message: discord.Message
    setup_type: SetupType = None


@dataclass
class UserInput:
    type: SetupInputType = SetupInputType.NONE
    prepared_input: PreparedInput = None
