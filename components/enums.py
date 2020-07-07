from enum import Enum


class ConfigStatus(Enum):
    OTHER = 0
    OPTION_DOES_NOT_EXIST = 1
    CONVERSION_FAILED = 2
    NOT_IN_VALID_LIST = 3
    UNKNOWN_DATA_TYPE = 4
    NOT_VALID_FOR_DATA_TYPE = 5
    TEXT_CHANNEL_NOT_FOUND = 6
    ROLE_NOT_FOUND = 7
    SAVE_SUCCESS = 10
    SAVE_FAIL = 11


class AmadeusMenuStatus(Enum):
    NEW = 0
    SHOWN = 1
    CANCELLED = 2
    TIMEOUT = 3
    SELECTED = 4
