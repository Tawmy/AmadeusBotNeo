import json
import os
import sys
from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context

# alters sys path so importing the Base actually works later on
sys.path = ['', '..'] + sys.path[1:]

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.


config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata


def get_target_metadata():
    from database.models import Base
    return Base.metadata


target_metadata = get_target_metadata()


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    json_config = get_bot_config()
    if json_config is None:
        return
    driver = json_config["database"]["driver"]
    username = os.environ['POSTGRES_USER']
    password = os.environ['POSTGRES_PASSWORD']
    address = os.environ['DB_IP']
    db_name = os.environ['POSTGRES_DB']
    url = f"{driver}://{username}:{password}@{address}/{db_name}"
    return url


def get_bot_config():
    json_data = None
    with open("config/bot.json", 'r') as file:
        try:
            json_data = json.load(file)
            print("Configuration file loaded successfully into alembic")
        except ValueError as e:
            raise SystemExit(e)
    return json_data


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = create_engine(get_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

