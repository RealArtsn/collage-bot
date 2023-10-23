import discord
from discord import app_commands
import logging, sys, os
from datetime import datetime
from PIL import Image
from PIL import UnidentifiedImageError
import urllib.request as urllib
import io, random

class Client(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        # sync commands if 'sync' argument provided
        if 'sync' in sys.argv:
            print('Syncing slash commands globally...')
            await bot.tree.sync()
            print('Exiting...')
            await self.close()

# create bot instance
bot = Client(intents=discord.Intents.default())

# set up slash command tree
bot.tree = app_commands.CommandTree(bot)

# initialize a 'busy' variable
bot.busy = False

# create log directory if not exists
try:
    os.mkdir('logs')
except FileExistsError:
    pass

# logging handler
bot.log_handler = logging.FileHandler(filename=f'logs/{datetime.now().strftime("%y%m%d%H%M%S")}_discord.log', encoding='utf-8', mode='w')

# collage slash command
@bot.tree.command(name = "collage", description = "View or paste image in server collage.")
async def slash(interaction:discord.Interaction, image_url: str = None, attachment:discord.Attachment = None):
    # stop interaction if bot is busy
    if bot.busy:
        await interaction.response.send_message("I'm busy, give me a second.", ephemeral=True)
        return
    # mark bot as busy
    bot.busy = True
    # get path to current background image
    guild_canvas_path = f'resources/{interaction.guild.id}_collage.png'
    # use blank canvas if guild canvas does not exist
    if not os.path.exists(guild_canvas_path):
        old_canvas_path = 'resources/blank_canvas.png'
    else:
        old_canvas_path = guild_canvas_path
    # send canvas and return if no attached image
    if not image_url and not attachment:
        await interaction.response.send_message(file=discord.File(old_canvas_path))
        bot.busy = False
        return
    # place image on collage from image url
    if attachment and not image_url:
        image_url = attachment.url
        print(image_url)
    
    try:
        image_pil = pil_from_url(image_url)
    except (ValueError, UnidentifiedImageError):
        await interaction.response.send_message('Invalid URL', ephemeral=True)
        return
    place_image(image_pil, guild_canvas_path)
    await interaction.response.send_message(file=discord.File(guild_canvas_path))
    message = await discord.utils.get(interaction.channel.history(), author__id=bot.user.id)
    
    with open(f'resources/{interaction.guild.id}_images.txt', 'a') as f:
        f.write(message.attachments[0].url.split('?')[0] + '\n')
    # mark bot as no longer busy
    bot.busy = False

# retrieve pillow image from url
def pil_from_url(image_url):
    hdr = {'User-Agent':'Mozilla/5.0'}
    req = urllib.Request(image_url,headers=hdr)
    fd = urllib.urlopen(req)
    image_file = io.BytesIO(fd.read())
    return Image.open(image_file)

# place provided image on top of the canvas
def place_image(pil_image, canvas_path):
    TEMPLATE_PATH = 'resources/blank_canvas.png'
    canvas = Image.open(canvas_path if os.path.exists(canvas_path) else TEMPLATE_PATH)
    resize_image(pil_image, random.random() * calc_max_scale(canvas, pil_image)) #helpo
    canvas.paste(pil_image, find_random_place(canvas, pil_image))
    canvas.save(canvas_path)
    return

# calculate the maximum length/height of placed image
def calc_max_scale(canvas, image, ratio=0.4):
    max_scale = [0,0]
    for i in range(2):
        max_scale[i] = (canvas.size[i] * ratio) / image.size[i]
    return min(max_scale)
    
# resize image by scalar
def resize_image(pil_image, scale):
    new_size = (side * scale for side in pil_image.size)
    pil_image.thumbnail(new_size, Image.Resampling.LANCZOS)

# find random coordinate on canvas for image placement
def find_random_place(canvas, image):
    x = random.randint(0, canvas.size[0] - image.size[0])
    y = random.randint(0, canvas.size[1] - image.size[1])
    return (x, y)

# Run with token or prompt if one does not exist
try:
    with open('token', 'r') as token:
        bot.run(token.read(), log_handler=bot.log_handler, log_level=logging.DEBUG)
except FileNotFoundError:
    print('Token not found. Input bot token and press enter or place it in a plaintext file named `token`.')
    token_text = input('Paste token: ')
    with open('token','w') as token:
        token.write(token_text)
        bot.run(token_text, log_handler=bot.log_handler, log_level=logging.DEBUG)
