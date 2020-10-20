from functools import reduce
from typing import Any


async def deep_get(dictionary: dict, *keys) -> Any:
    """
    Gets value for nested dictionaries

    Parameters
    ----------
    dictionary: dict
    keys: List[str]

    Returns
    -------
    Value if found, None if not
    """
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)


async def deep_get_type(data_type: type, dictionary: dict, *keys) -> Any:
    """
    Gets value for nested dictionaries with a fallback type

    Parameters
    ----------
    data_type: type
    dictionary: dict
    keys: List[str]

    Returns
    -------
    Value if found, default for given type if not
    """
    result = await deep_get(dictionary, *keys)
    if result is None:
        if data_type == dict:
            return {}
        elif data_type == list:
            return []
        elif data_type == str:
            return ""
    return result
