from enum import Enum


class ConfigStep(Enum):
    NO_INFO = 0
    CATEGORY = 1
    OPTION = 2
    CATEGORY_OPTION = 3
    CATEGORY_OPTION_CONFIRMED = 4
    CATEGORY_OPTION_CANCELLED = 5
    CATEGORY_OPTION_VALUE = 6
    CATEGORY_OPTION_SETDEFAULT = 7
    FINISHED = 10


class ConfigStatus(Enum):
    OTHER = 0
    OPTION_DOES_NOT_EXIST = 1
    CONVERSION_FAILED = 2
    NOT_IN_VALID_LIST = 3
    UNKNOWN_DATA_TYPE = 4
    NOT_VALID_FOR_DATA_TYPE = 5
    TEXT_CHANNEL_NOT_FOUND = 6
    ROLE_NOT_FOUND = 7
    PREPARATION_SUCCESSFUL = 10
    SAVE_SUCCESS = 11
    SAVE_FAIL = 12


class ReturnType(Enum):
    DEFAULT_VALUE = 0
    SERVER_VALUE = 1


class Datatype(Enum):
    CUSTOM = 0
    BOOLEAN = 1
    STRING = 2
    INTEGER = 3
    ROLE = 4
    TEXT_CHANNEL = 5
    VOICE_CHANNEL = 6


class InputType(Enum):
    ANY = 0
    AS_DATATYPE = 1
    AS_VALID_LIST = 2
    TO_BE_CONVERTED = 3


class SetupType(Enum):
    REGULAR = 0
    FULL_RESET = 1
    CANCELLED = 2


class SetupInputType(Enum):
    NONE = 0
    OK = 1
    WRONG = 2
    CANCELLED = 3


class SetupStatus(Enum):
    CANCELLED = 0
    SUCCESSFUL = 1
    SAVE_FAILED = 2
