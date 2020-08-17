from functools import reduce


async def deep_get(dictionary, *keys):
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)


async def deep_get_type(type, dictionary, *keys):
    result = await deep_get(dictionary, *keys)
    if result is None:
        if type == dict:
            return {}
        elif type == list:
            return []
    return result
