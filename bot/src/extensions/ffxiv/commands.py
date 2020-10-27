from PIL import Image, ImageDraw
from discord.ext import commands
from discord.ext.commands import Context
from extensions.ffxiv.functions import ffchar


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ffchar')
    async def ffchar(self, ctx: Context, first_name: str, last_name: str, server: str):
        async with ctx.typing():
            character_id = await ffchar.find_character(ctx, first_name, last_name, server)
            if character_id is None:
                return  # TODO show status

            # load character data based on ID from __find_character
            character_raw = await ffchar.request_character_data(ctx, character_id)
            if character_raw is None:
                # TODO handle this
                print("character was none")
                return

            character = await ffchar.get_character(ctx, character_raw)
            # load background image, download character image, merge them
            image = Image.open("resources/ffxiv/ffchar.png")
            await ffchar.crop_character_portrait(image, character)
            await ffchar.load_character_frame(image)

            draw = ImageDraw.Draw(image)
            await ffchar.add_text_to_image(ctx, draw, image, character)

            await ffchar.send_character_sheet(ctx, image, character)


def setup(bot):
    bot.add_cog(FFXIV(bot))
