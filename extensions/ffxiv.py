from dataclasses import dataclass
from io import BytesIO

import pyxivapi
import requests
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ffchar')
    async def ffchar(self, ctx, first_name: str, last_name: str, server: str):
        character_id = await self.__find_character(first_name, last_name, server)
        if character_id is None:
            return  # TODO show status

        # load character data based on ID from __find_character
        character = await self.__request_character_data(character_id)

        # load background image, download character image, merge them
        image = await self.__load_images(character)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('resources/OpenSans-Regular.ttf', size=24)

        # add character name, fc when applicable, title when applicable
        await self.__add_character_name(draw, character)

        # add job levels
        await self.__add_job_levels(draw, font, character)


        await self.__add_grand_company(image, character)


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

    async def __load_images(self, character: dict):
        template = Image.open("resources/ffchar.png")
        background = Image.new('RGB', template.size, color='grey')
        response = requests.get(character.get("Character", {}).get("Portrait"))
        character = Image.open(BytesIO(response.content))
        character = character.crop((40, 0, 600, 873))
        # portrait height is 873px, hence the 27 above
        background.paste(character, (0, background.height - character.height))
        background.paste(template, (0, 0), template)
        return background

    async def __add_character_name(self, draw: ImageDraw.Draw, character: dict):
        name = character.get("Character", {}).get("Name")
        title = character.get("Character", {}).get("Title", {}).get("Name")

        if len(title) > 0:
            title = "<" + title + ">"
            if character.get("Character", {}).get("TitleTop"):
                cat = "title_top"
            else:
                cat = "title_bot"
            x_title, y_title = self.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("title").values()
            font = ImageFont.truetype('resources/OpenSans-Regular.ttf', size=24)
            await self.__print_text_centered_at_point(draw, font, title, x_title, y_title)
        else:
            cat = "no_title"

        x_name, y_name = self.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("name").values()
        font = ImageFont.truetype('resources/OpenSans-Regular.ttf', size=38)
        await self.__print_text_centered_at_point(draw, font, name, x_name, y_name)

    async def __print_text_centered_at_point(self, draw, font, text, x, y):
        text_size_x, text_size_y = draw.textsize(text, font=font)
        draw.text((x - text_size_x / 2, y - text_size_y / 2), text, fill='rgb(0, 0, 0)', font=font)

    async def __add_job_levels(self, draw, font, character):
        for ff_class in character.get("Character", {}).get("ClassJobs"):
            abbr = ff_class.get("Job", {}).get("Abbreviation")
            x, y = self.bot.ffxiv.get("JobPositions", {}).get(abbr).values()
            level = ff_class.get("Level")
            if level == 0:
                text = "-"
            else:
                text = str(level)
            txt_length_x, txt_length_y = draw.textsize(text, font=font)
            draw.text((x - txt_length_x / 2, y - txt_length_y / 2), text, fill='rgb(255, 255, 255)', font=font)

    async def __add_grand_company(self, image, character):
        gc = character.get("Character", {}).get("GrandCompany", {}).get("Company", {}).get("Name")
        if gc is not None and len(gc) > 0:
            filename = ""
            if gc == "Maelstrom":
                filename = "gc_m"
            elif gc == "Order of the Twin Adder":
                filename = "gc_o"
            elif gc == "Immortal Flames":
                filename = "gc_i"
            if len(filename) > 0:
                gc_icon = Image.open("resources/" + filename + ".png")
                x, y = self.bot.ffxiv.get("Positions", {}).get("grand_company").values()
                image.paste(gc_icon, (x, y), gc_icon)



def setup(bot):
    bot.add_cog(FFXIV(bot))
