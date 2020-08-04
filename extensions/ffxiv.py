from dataclasses import dataclass
from io import BytesIO

import pyxivapi
import requests
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands


@dataclass
class Values:
    name_top_y = 18
    name_bottom_y = 48


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.values = Values()

    @commands.command(name='ffchar')
    async def ffchar(self, ctx, first_name: str, last_name: str, server: str):
        character_id = await self.__find_character(first_name, last_name, server)
        if character_id is None:
            return  # TODO show status

        # load character data based on ID from __find_character
        character = await self.__request_character_data(character_id)

        # load background image, download character image, merge them
        image = await self.__load_image(character)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('resources/OpenSans-Regular.ttf', size=24)

        # add character name, fc when applicable, title when applicable
        await self.__add_character_name(draw, font, character, image.width)

        # level_whm = str(character.get("Character", {}).get("ClassJobs", {})[8].get("Level"))
        # draw.text((1465, 115), level_whm, fill='rgb(255, 255, 255)', font=font)

        # level_sch = str(character.get("Character", {}).get("ClassJobs", {})[9].get("Level"))
        # draw.text((1350, 115), level_sch, fill='rgb(255, 255, 255)', font=font)

        # level_ast = str(character.get("Character", {}).get("ClassJobs", {})[10].get("Level"))
        # draw.text((1600, 115), level_ast, fill='rgb(255, 255, 255)', font=font)

        # image.save('rocket_pillow_paste_pos.jpg', quality=95)

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
            include_classjobs=True
        )
        # TODO check behaviour when character ID does not exist
        await client.session.close()
        if character is not None:
            return character
        return None

    async def __load_image(self, character: dict):
        background = Image.open("resources/ffchar.jpg")
        response = requests.get(character.get("Character", {}).get("Portrait"))
        character = Image.open(BytesIO(response.content))
        # portrait height is 873px, hence the 27 above
        position_w = int(background.width / 2 - character.width / 2)
        background.paste(character, (position_w, background.height - character.height))
        return background

    async def __add_character_name(self, draw: ImageDraw.Draw, font: ImageFont.truetype, character: dict, width: int):
        name = character.get("Character", {}).get("Name")
        name_position_y = self.values.name_bottom_y
        if character.get("FreeCompany") is not None:
            name += " <<" + character.get("FreeCompany", {}).get("Tag") + ">>"
        font_width_name, font_height_name = draw.textsize(name, font=font)
        title = character.get("Character", {}).get("Title", {}).get("Name")
        if len(title) > 0:
            title = "<" + title + ">"
            font_width_title, font_height_title = draw.textsize(title, font=font)
            if character.get("Character", {}).get("TitleTop"):
                title_position_y = self.values.name_top_y
            else:
                name_position_y = self.values.name_top_y
                title_position_y = self.values.name_bottom_y
            draw.text((width / 2 - font_width_title / 2, title_position_y), title, fill='rgb(255, 255, 255)', font=font)
        draw.text((width / 2 - font_width_name / 2, name_position_y), name, fill='rgb(255, 255, 255)', font=font)


def setup(bot):
    bot.add_cog(FFXIV(bot))
