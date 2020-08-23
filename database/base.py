from alembic import config, script
from alembic.runtime import migration
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import ScopedSession


async def check_if_db_up_to_date(bot):
    engine = create_engine(await get_url(bot))
    script_ = script.ScriptDirectory.from_config(config.Config('alembic.ini'))
    with engine.begin() as conn:
        context = migration.MigrationContext.configure(conn)
        return context.get_current_revision() == script_.get_current_head()


async def upgrade_database():
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head'
    ]
    config.main(argv=alembic_args)


async def init_session(bot):
    session = ScopedSession(sessionmaker())
    engine = create_engine(await get_url(bot))
    session.configure(bind=engine)
    bot.db_session = session
    pass


async def get_url(bot):
    driver = bot.config["bot"]["database"]["driver"]
    username = bot.config["bot"]["database"]["username"]
    password = bot.config["bot"]["database"]["password"]
    address = bot.config["bot"]["database"]["address"]
    db_name = bot.config["bot"]["database"]["db_name"]
    url = f"{driver}://{username}:{password}@{address}/{db_name}"
    return url
