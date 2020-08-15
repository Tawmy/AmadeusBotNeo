import datetime
from io import BytesIO

import pyxivapi
from PIL import Image, ImageDraw
from discord import File
from discord.ext import commands
from discord.ext.commands import Context

from helpers import ffxiv_draw as ffd, ffxiv_character as ffc
from helpers.ffxiv_character import Character


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ffchar')
    async def ffchar(self, ctx: Context, first_name: str, last_name: str, server: str):
        async with ctx.typing():
            character_id = await self.__find_character(first_name, last_name, server)
            if character_id is None:
                return  # TODO show status

            # load character data based on ID from __find_character
            character_raw = await self.__request_character_data(character_id)
            if character_raw is None:
                # TODO handle this
                print("character was none")
                return

            character = await ffc.get_character(ctx, character_raw)
            # load background image, download character image, merge them
            image = Image.open("resources/ffxiv/ffchar.png")
            await self.__crop_character_portrait(image, character)
            await self.__load_character_frame(image)

            draw = ImageDraw.Draw(image)
            await self.__add_text_to_image(ctx, draw, image, character)

            await self.__send_character_sheet(ctx, image, character)

    async def __add_text_to_image(self, ctx: Context, draw: ImageDraw, image: Image, character: Character):
        await ffd.add_character_name(ctx, draw, character)
        await ffd.add_job_levels(ctx, draw, character)
        await ffd.add_grand_company(ctx, draw, image, character)
        await ffd.add_free_company(ctx, draw, character)
        await ffd.add_active_class_job(ctx, image, character)
        await ffd.add_item_level(ctx, draw, character)
        await ffd.add_mount_percentage(ctx, draw, character)
        await ffd.add_minion_percentage(ctx, draw, character)
        await ffd.add_server(ctx, draw, character)
        await ffd.add_attributes(ctx, draw, character)

    async def __find_character(self, first_name: str, last_name: str, server: str):
        client = pyxivapi.XIVAPIClient(api_key=self.bot.config["bot"]["ffxiv"]["api_key"])
        character = await client.character_search(
            world=server,
            forename=first_name,
            surname=last_name,
        )
        await client.session.close()
        if len(character.get("Results")) > 0:
            return character.get("Results")[0].get("ID")
        return None

    async def __request_character_data(self, character_id: int):
        client = pyxivapi.XIVAPIClient(api_key=self.bot.config["bot"]["ffxiv"]["api_key"])
        character = await client.character_by_id(
            lodestone_id=character_id,
            extended=True,  # extended includes title string, not just id
            include_freecompany=True,
            include_classjobs=True,
            include_minions_mounts=True
        )
        # TODO check behaviour when character ID does not exist
        await client.session.close()
        if character is not None:
            return character
        return None

    async def __crop_character_portrait(self, background: Image, character: Character):
        portrait = character.portrait.crop((63, 0, 577, 873))
        portrait = portrait.resize((459, 780))
        background.paste(portrait, (18, 64))

    async def __load_character_frame(self, background: Image):
        frame = Image.open("resources/ffxiv/frame.png")
        background.paste(frame, (18, 22), frame)

    async def __send_character_sheet(self, ctx: Context, image: ImageDraw, character: Character):
        filename = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S") + "_"
        filename += character.name.name + ".jpg"
        with BytesIO() as image_binary:
            image.save(image_binary, 'JPEG', quality=90)
            image_binary.seek(0)
            await ctx.send(file=File(fp=image_binary, filename=filename))


def setup(bot):
    bot.add_cog(FFXIV(bot))
