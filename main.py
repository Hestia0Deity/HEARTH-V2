import dotenv, os, discord, asyncio
from discord.ext import commands
from cogs.verification import TagButtons
from cogs.submissions import submissionButtons


# Gets and loads the information from .env for os
dotenv.load_dotenv()

# Establishes the discord client
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

## Loading the bot cogs.
async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f'cogs.{filename[:-3]}')

# Setup hook
async def setup_hook():
    client.add_view(TagButtons())
    client.add_view(submissionButtons())

client.setup_hook = setup_hook

# Syncing commands
@client.command()
async def sync(ctx):
    if ctx.author.id == 746931991827447818:
        fmt = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(fmt)} commands.")
    
# Running the bot
asyncio.run(load())
client.run(os.environ.get('BTOKEN'))