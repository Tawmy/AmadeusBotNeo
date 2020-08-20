from functools import reduce


async def deep_get(dictionary, *keys):
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


async def deep_get_type(data_type, dictionary, *keys):
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
    return result
