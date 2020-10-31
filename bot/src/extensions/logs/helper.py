from discord.ext.commands import Bot

from database.models import User


async def is_image(url: str) -> bool:
    # TODO check which image types are supported
    if url[-4:] in [".jpg", ".png"]:
        return True
    if url[-5:] in [".jpeg", ".webp"]:
        return True
    return False


async def add_user(bot: Bot, user_id: int):
    db_entry = User()
    db_entry.id = user_id
    bot.db_session.add(db_entry)
