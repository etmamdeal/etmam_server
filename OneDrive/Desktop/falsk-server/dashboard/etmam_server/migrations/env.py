from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# if config.config_file_name is not None:
#    fileConfig(config.config_file_name) # Commented out to bypass 'formatters' KeyError

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# For Flask-SQLAlchemy, it's usually found like this:
from flask import current_app
config.set_main_option('sqlalchemy.url',
                       current_app.config.get('SQLALCHEMY_DATABASE_URI'))
target_metadata = current_app.extensions['migrate'].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # include_object is used to filter objects for autogenerate
        # include_object=include_object,
        # process_revision_directives is used to process revision directives
        # process_revision_directives=process_revision_directives,
        compare_type=True, # Recommended for detecting type changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # include_object=include_object,
            # process_revision_directives=process_revision_directives,
            compare_type=True, # Recommended for detecting type changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# Example of include_object function for filtering specific tables (optional)
# def include_object(object, name, type_, reflected, compare_to):
#     if type_ == "table" and name == "special_table":
#         return False
#     else:
#         return True

# Example of process_revision_directives function (optional)
# def process_revision_directives(context, revision, directives):
#     if getattr(config.cmd_opts, 'autogenerate', False):
#         script = directives[0]
#         if script.upgrade_ops.is_empty():
#             directives[:] = []
#             print('No changes in schema detected.')
