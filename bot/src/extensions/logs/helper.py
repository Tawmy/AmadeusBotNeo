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
    db_object = bot.db_session.query(User).filter_by(id=user_id).first()
    if db_object:
        return
    else:
        db_entry = User()
        db_entry.id = user_id
        bot.db_session.add(db_entry)
        bot.db_session.commit()
