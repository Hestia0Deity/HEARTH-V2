import discord, sqlite3, os, dotenv, random, re
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# Delete these if not necessary
db = sqlite3.connect("main.db")
cursor = db.cursor()

# Main class
class template(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # db.execute(f"CREATE TABLE IF NOT EXISTS _____Database(guildID INT, element ELEMENT)")
        # db.commit()
        print("template.py -- ONLINE")
        
# Sets the actual cogs up.
async def setup(bot):
    await bot.add_cog(template(bot))