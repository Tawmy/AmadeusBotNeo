from enum import Enum


class AmadeusMenuStatus(Enum):
    NEW = 0
    SHOWN = 1
    CANCELLED = 2
    TIMEOUT = 3
    SELECTED = 4


class AmadeusPromptStatus(Enum):
    NEW = 0
    SHOWN = 1
    CANCELLED = 2
    TIMEOUT = 3
    INPUT_GIVEN = 4
