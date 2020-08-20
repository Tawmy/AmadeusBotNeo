from functools import reduce


async def deep_get(dictionary, *keys):
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)


async def deep_get_type(data_type, dictionary, *keys):
    result = await deep_get(dictionary, *keys)
    if result is None:
        if data_type == dict:
            return {}
        elif data_type == list:
            return []
    return result
