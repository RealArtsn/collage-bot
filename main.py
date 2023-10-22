import discord
from discord import app_commands
import logging, sys, os
from datetime import datetime

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

# create log directory if not exists
try:
    os.mkdir('logs')
except FileExistsError:
    pass

# logging handler
bot.log_handler = logging.FileHandler(filename=f'logs/{datetime.now().strftime("%y%m%d%H%M%S")}_discord.log', encoding='utf-8', mode='w')

# collage slash command
@bot.tree.command(name = "collage", description = "View or paste image in server collage.")
@app_commands.choices(stretch=[
    app_commands.Choice(name = 'True', value='True'),
    app_commands.Choice(name = 'False', value='')
    ])
async def slash(interaction:discord.Interaction, image_url: str = None, attachment:discord.Attachment = None, stretch: app_commands.Choice[str] = ''):
    if not image_url or attachment:
        image_path = f'resources/{interaction.guild.id}_collage.png'
        if not os.path.exists(image_path):
            image_path = 'resources/blank_canvas.png'
        await interaction.response.send_message(file=discord.File(image_path))

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
