import datetime
from dataclasses import dataclass
from io import BytesIO

import pyxivapi
import requests
from PIL import Image, ImageDraw, ImageFont
from discord import File
from discord.ext import commands
from helpers import ffxiv_draw as ff


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ffchar')
    async def ffchar(self, ctx, first_name: str, last_name: str, server: str):
        async with ctx.typing():
            character_id = await self.__find_character(first_name, last_name, server)
            if character_id is None:
                return  # TODO show status

            # load character data based on ID from __find_character
            character = await self.__request_character_data(character_id)
            if character is None:
                # TODO handle this
                print("character was none")
                return

            # load background image, download character image, merge them
            image = await self.__load_background()
            await self.__load_character_portrait(image, character)
            await self.__load_character_frame(image)

            draw = ImageDraw.Draw(image)
            await self.__add_text_to_image(ctx, draw, image, character)

            await self.__send_character_sheet(ctx, image, character)

    async def __add_text_to_image(self, ctx, draw, image, character):
        await ff.add_character_name(ctx, draw, character)
        await ff.add_job_levels(ctx, draw, character)
        await ff.add_grand_company(ctx, draw, image, character)
        await ff.add_free_company(ctx, draw, character)
        await ff.add_active_class_job(ctx, image, character)
        await ff.add_item_level(ctx, draw, character)
        await ff.add_mount_and_minion_percentages(ctx, draw, character)
        await ff.add_server(ctx, draw, character)
        await ff.add_attributes(ctx, draw, character)

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

    async def __load_background(self) -> Image:
        return Image.open("resources/ffxiv/ffchar.png")

    async def __load_character_portrait(self, background: Image, character: dict):
        response = requests.get(character.get("Character", {}).get("Portrait"))
        portrait = Image.open(BytesIO(response.content))
        portrait = portrait.crop((63, 0, 577, 873))
        portrait = portrait.resize((459, 780))
        background.paste(portrait, (18, 64))

    async def __load_character_frame(self, background: Image):
        frame = Image.open("resources/ffxiv/frame.png")
        background.paste(frame, (18, 22), frame)

    async def __send_character_sheet(self, ctx, image, character):
        filename = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S") + "_"
        filename += character.get("Character", {}).get("Name") + ".jpg"
        with BytesIO() as image_binary:
            image.save(image_binary, 'JPEG', quality=90)
            image_binary.seek(0)
            await ctx.send(file=File(fp=image_binary, filename=filename))


def setup(bot):
    bot.add_cog(FFXIV(bot))
