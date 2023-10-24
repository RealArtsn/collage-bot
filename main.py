import discord
from discord import app_commands
from discord.ext import commands, tasks
import logging, sys, os
from datetime import datetime
from PIL import Image
from PIL import UnidentifiedImageError
import urllib.request as urllib
import io, random

class Client(discord.Client):
    def __init__(self, *args, **kwargs):
        super(Client, self).__init__(*args, **kwargs)
        # set up slash command tree
        self.tree = app_commands.CommandTree(self)
        # collage slash command
        @self.tree.command(name = "collage", description = "View or paste image in server collage.")
        async def slash(interaction:discord.Interaction, image_url: str = None, attachment:discord.Attachment = None):
            # hold interaction
            await interaction.response.defer(ephemeral=False)
            # add to queue
            self.queue.append((interaction, image_url, attachment))

        # initialize queue
        self.queue = []
        
        # initialize a 'busy' variable
        self.busy = False

        # create log directory if not exists
        try:
            os.mkdir('logs')
        except FileExistsError:
            pass
        # logging handler
        self.log_handler = logging.FileHandler(filename=f'logs/{self.generate_timestamp()}_discord.log', encoding='utf-8', mode='w')

        # Run with token or prompt if one does not exist
        try:
            with open('token', 'r') as token:
                self.run(token.read(), log_handler=self.log_handler, log_level=logging.DEBUG)
        except FileNotFoundError:
            print('Token not found. Input bot token and press enter or place it in a plaintext file named `token`.')
            token_text = input('Paste token: ')
            with open('token','w') as token:
                token.write(token_text)
                self.run(token_text, log_handler=self.log_handler, log_level=logging.DEBUG)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        # sync commands if 'sync' argument provided
        if 'sync' in sys.argv:
            print('Syncing slash commands globally...')
            await self.tree.sync()
            print('Exiting...')
            await self.close()
        # define queue event loop
        @tasks.loop(seconds=0.2)
        async def task(self):
            if self.busy or (len(self.queue) == 0):
                return
            await self.handle_interaction(*self.queue.pop(0))
        # start queue event loop
        await task.start(self)

    # generate a blank canvas and pass as pil image
    def generate_canvas(self, dimensions=(1920,1080)):
        return Image.new('RGBA', dimensions, (0,0,0,0))
    
    # resize image by scalar
    def resize_image(self, pil_image: Image.Image, scale: float):
        new_size = (side * scale for side in pil_image.size)
        pil_image.thumbnail(new_size, Image.Resampling.LANCZOS)

    # retrieve pillow image from url
    def pil_from_url(self, image_url):
        hdr = {'User-Agent':'Mozilla/5.0'}
        req = urllib.Request(image_url,headers=hdr)
        fd = urllib.urlopen(req)
        image_file = io.BytesIO(fd.read())
        return Image.open(image_file).convert('RGBA')

    # place provided image on top of the canvas
    def place_image(self, pil_image: Image.Image, canvas: Image.Image):
        self.resize_image(pil_image, random.random() * self.calc_max_scale(canvas, pil_image))
        canvas.paste(pil_image, self.find_random_place(canvas, pil_image), pil_image)
        return canvas

    # convert PIL image to discord file
    def pil_to_discord(self, pil_image: Image.Image, filename='image.png'):
        img_bytes = io.BytesIO()
        pil_image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return discord.File(img_bytes, filename=filename)

    # calculate the maximum length/height of placed image
    def calc_max_scale(self, canvas, image, ratio=0.4):
        max_scale = [0,0]
        for i in range(2):
            max_scale[i] = (canvas.size[i] * ratio) / image.size[i]
        return min(max_scale)
        
    # find random coordinate on canvas for image placement
    def find_random_place(self, canvas, image):
        x = random.randint(0, canvas.size[0] - image.size[0])
        y = random.randint(0, canvas.size[1] - image.size[1])
        return (x, y)

    # retrieve canvas pil image from guild id
    def get_or_generate_canvas(self, guild_id):
        links_path = f'resources/{guild_id}_images.txt'
        if not os.path.exists(links_path):
            print(f'Generating canvas for {guild_id}')
            return self.generate_canvas()
        with open(links_path, 'r') as f:
            link = f.readlines()[-1]
        try:
            print(link)
            return self.pil_from_url(link)
        except UnidentifiedImageError:
            return self.generate_canvas()
    
    # generate timestamp for filenames
    def generate_timestamp(self):
        return datetime.now().strftime("%y%m%d%H%M%S")
    
    # handle slash command interaction
    async def handle_interaction(self, interaction: discord.Interaction, image_url:str, attachment:discord.Attachment):
        # stop interaction if bot is busy
        if self.busy:
            await interaction.followup.send("I'm busy, give me a second.", ephemeral=True)
            return
        # mark bot as busy
        self.busy = True

        # get the canvas image or deny if not valid guild
        try:
            canvas = self.get_or_generate_canvas(interaction.guild.id)
        except AttributeError:
            await interaction.followup.send("Invalid guild.")
            self.busy = False
            return

        # send canvas and return if no attached image
        if not image_url and not attachment:
            await interaction.followup.send(file=self.pil_to_discord(canvas))
            self.busy = False
            return
        
        # retrieve image from attached url
        if attachment and not image_url:
            image_url = attachment.url
        try:
            image_pil = self.pil_from_url(image_url)
        except (ValueError, UnidentifiedImageError):
            await interaction.followup.send('Invalid URL', ephemeral=True)
            self.busy = False
            return
        
        # place provided image on the canvas and send
        try:
            self.place_image(image_pil, canvas)
        except Exception as e:
            await interaction.followup.send(f'Uh oh! {e}')
            self.busy = False
            return
        await interaction.followup.send(file=self.pil_to_discord(canvas, f'{self.generate_timestamp()}_{interaction.guild_id}_canvas.png'))

        # retrieve message sent by bot
        message = await interaction.original_response()
        
        # write url of sent image to file
        with open(f'resources/{interaction.guild.id}_images.txt', 'a') as f:
            f.write(message.attachments[0].url.split('?')[0] + '\n')
        # mark bot as no longer busy
        self.busy = False
        return

# initialize bot object
Client(intents=discord.Intents.default())
