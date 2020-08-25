from dataclasses import dataclass

import discord

from extensions.config.dataclasses import PreparedInput
from extensions.setup.enums import SetupType, InputType


@dataclass
class SetupTypeSelection:
    message: discord.Message
    setup_type: SetupType = None


@dataclass
class UserInput:
    type: InputType = InputType.NONE
    prepared_input: PreparedInput = None
