from discord.ext import commands


class Base(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        db_guilds = await self.request_guild_ids()

        in_database = False
        for db_guild in db_guilds:
            if db_guild["id"] == guild.id:
                in_database = True

        if in_database is False:
            await self.upsert_guild(guild)

    async def request_guild_ids(self):
        sql = '''   SELECT id
                    FROM guilds'''

        con = await self.bot.database_pool.acquire()
        try:
            return await con.fetch(sql)
        finally:
            await self.bot.database_pool.release(con)

    async def upsert_guild(self, guild):
        sql = '''   INSERT INTO guilds (id, name)
                    VALUES ($1::bigint, $2::text)
                    ON CONFLICT (id)
                    DO UPDATE SET id = $1::bigint, name = $2::text'''
        con = await self.bot.database_pool.acquire()
        try:
            await con.execute(sql, guild.id, guild.name)
        finally:
            await self.bot.database_pool.release(con)


def setup(bot):
    bot.add_cog(Base(bot))
