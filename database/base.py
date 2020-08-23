from enum import Enum

from alembic import config, script
from alembic.runtime import migration
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import ScopedSession


class DatabaseVersionStatus(Enum):
    UP_TO_DATE = 0
    OUT_OF_DATE = 1
    NO_CONNECTION = 2


async def check_if_db_up_to_date(bot) -> DatabaseVersionStatus:
    timeout = bot.config["bot"]["database"]["timeout"]
    engine = create_engine(await get_url(bot), connect_args={'connect_timeout': timeout})
    script_ = script.ScriptDirectory.from_config(config.Config('alembic.ini'))
    try:
        with engine.begin() as conn:
            context = migration.MigrationContext.configure(conn)
            if context.get_current_revision() == script_.get_current_head():
                return DatabaseVersionStatus.UP_TO_DATE
            else:
                return DatabaseVersionStatus.OUT_OF_DATE
    except OperationalError:
        return DatabaseVersionStatus.NO_CONNECTION


async def upgrade_database():
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head'
    ]
    config.main(argv=alembic_args)


async def init_session(bot):
    session = ScopedSession(sessionmaker())
    timeout = bot.config["bot"]["database"]["timeout"]
    engine = create_engine(await get_url(bot), connect_args={'connect_timeout': timeout})
    session.configure(bind=engine)
    if await validate_session(session) is True:
        bot.db_session = session


async def validate_session(session):
    try:
        session.connection()
        return True
    except OperationalError:
        return False


async def get_url(bot):
    driver = bot.config["bot"]["database"]["driver"]
    username = bot.config["bot"]["database"]["username"]
    password = bot.config["bot"]["database"]["password"]
    address = bot.config["bot"]["database"]["address"]
    db_name = bot.config["bot"]["database"]["db_name"]
    url = f"{driver}://{username}:{password}@{address}/{db_name}"
    return url
