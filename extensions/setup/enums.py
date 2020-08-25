from enum import Enum


class SetupType(Enum):
    REGULAR = 0
    FULL_RESET = 1
    CANCELLED = 2


class InputType(Enum):
    NONE = 0
    OK = 1
    WRONG = 2
    CANCELLED = 3


class SetupStatus(Enum):
    CANCELLED = 0
    SUCCESSFUL = 1
    SAVE_FAILED = 2
