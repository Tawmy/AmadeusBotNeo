from enum import Enum


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


class LimitStatus(Enum):
    OTHER = 0
    NAME_NOT_FOUND = 1
    TEXT_CHANNEL_NOT_FOUND = 2
    ROLE_NOT_FOUND = 3
    PREPARATION_SUCCESSFUL = 4
    SAVE_SUCCESS = 5
    SAVE_FAIL = 6