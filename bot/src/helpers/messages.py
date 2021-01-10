from enum import Enum

from discord import Embed, HTTPException, Forbidden, TextChannel, Message, AllowedMentions
from discord.ext.commands import Context

from extensions.config import helper as c
from helpers import strings as s


class ErrorType(Enum):
    FORBIDDEN = 0
    HTTPEXCEPTION = 1


async def reply(ctx: Context, embed: Embed) -> Message:
    try:
        return await ctx.message.reply(embed=embed)
    except Forbidden:
        await __show_error_in_mod_channel(ctx, ErrorType.FORBIDDEN)
    except HTTPException:
        await __show_error_in_mod_channel(ctx, ErrorType.FORBIDDEN)


async def __show_error_in_mod_channel(ctx: Context, err_type: ErrorType):
    config = await c.get_config(ctx, "essential_channels", "mod_channel")
    channel = ctx.guild.get_channel(config.value)
    processed_string = None
    if err_type == err_type.FORBIDDEN:
        string = await s.get_string(ctx, "errors", "missing_permissions_message")
        strings_to_be_inserted = [ctx.channel.mention, ctx.bot.app_info.name]
        processed_string = await s.insert_into_string(strings_to_be_inserted, string.list)
    elif err_type == err_type.HTTPEXCEPTION:
        string = await s.get_string(ctx, "errors", "failed_to_send_message")
        processed_string = await s.insert_into_string([ctx.channel.mention], string.list)
    if processed_string is None or processed_string.successful is False:
        # do nothing if any other kind of error
        return

    try:
        await channel.send(processed_string.string_combined)
    except Forbidden:
        await __show_error_in_bot_channel(ctx, channel, processed_string.string_combined)
    except HTTPException:
        await __show_error_in_bot_channel(ctx, channel, processed_string.string_combined)


async def __show_error_in_bot_channel(ctx: Context, mod_channel: TextChannel, prev_string: str):
    config = await c.get_config(ctx, "essential_channels", "bot_channel")
    channel = ctx.guild.get_channel(config.value)
    string = await s.get_string(ctx, "errors", "missing_permissions_message_expansion")
    processed_string = await s.insert_into_string([mod_channel.mention], string.list)
    final_string = prev_string + processed_string.string_combined
    try:
        await channel.send(final_string)
    except Forbidden:
        await __dm_error_to_owner(ctx, mod_channel, channel, prev_string)
    except HTTPException:
        await __dm_error_to_owner(ctx, mod_channel, channel, prev_string)


async def __dm_error_to_owner(ctx: Context, mod_channel: TextChannel, bot_channel: TextChannel, prev_string: str):
    string = await s.get_string(ctx, "errors", "missing_permissions_message_expansion_two")
    strings_to_be_inserted = [mod_channel.mention, bot_channel.mention]
    processed_string = await s.insert_into_string(strings_to_be_inserted, string.list)
    final_string = prev_string + processed_string.string_combined
    try:
        await ctx.guild.owner.send(final_string)
    except HTTPException:
        pass # do nothing


async def edit(message: Message, embed: Embed) -> Message:
    allowed_mentions = AllowedMentions(everyone=False, roles=False, replied_user=False)
    return await message.edit(embed=embed, allowed_mentions=allowed_mentions)
    # TODO check permissions