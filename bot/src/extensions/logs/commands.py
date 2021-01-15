from discord import RawMessageDeleteEvent, RawMessageUpdateEvent, Member, User, RawBulkMessageDeleteEvent
from discord.ext import commands
from extensions.logs.functions import on_raw_message_delete, on_raw_message_edit, on_member_update_nick, \
    on_user_update_name, on_member_join, on_member_remove, on_member_update_pending, on_raw_bulk_message_delete, \
    on_user_update_avatar


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if self.bot.ready and payload.guild_id is not None:
            await on_raw_message_delete.log(self.bot, payload)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        if self.bot.ready and payload.guild_id is not None:
            await on_raw_bulk_message_delete.log(self.bot, payload)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        if payload.cached_message is not None:
            if payload.cached_message.author.id == self.bot.app_info.id:
                return
        else:
            author_id = payload.data.get("author", {}).get("id")
            if author_id is not None and int(author_id) == self.bot.app_info.id:
                return
        if self.bot.ready and "guild_id" in payload.data and payload.data["guild_id"] is not None and len(payload.data["guild_id"]) > 0:
            await on_raw_message_edit.log(self.bot, payload)

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.nick != after.nick:
            if self.bot.ready:
                await on_member_update_nick.log(self.bot, before, after)
        if before.pending is True and after.pending is False:
            if self.bot.ready:
                await on_member_update_pending.log(self.bot, before, after)

    @commands.Cog.listener()
    async def on_user_update(self, before: User, after: User):
        if before.name != after.name:
            if self.bot.ready:
                await on_user_update_name.iterate_and_log(self.bot, before, after)
        if before.avatar != after.avatar:
            await on_user_update_avatar.log(self.bot, before, after)

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if self.bot.ready:
            await on_member_join.log(self.bot, member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if self.bot.ready:
            await on_member_remove.log(self.bot, member)

def setup(bot):
    bot.add_cog(Logs(bot))
