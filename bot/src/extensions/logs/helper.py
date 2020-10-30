from datetime import datetime


async def is_image(url: str) -> bool:
    # TODO check which image types are supported
    if url[-4:] in [".jpg", ".png"]:
        return True
    if url[-5:] in [".jpeg", ".webp"]:
        return True
    return False
