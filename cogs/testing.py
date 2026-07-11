import discord, sqlite3, os, dotenv, random, re
from PIL import Image
from io import BytesIO
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# Delete these if not necessary
db = sqlite3.connect("main.db")
cursor = db.cursor()

# Main class
class testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # db.execute(f"CREATE TABLE IF NOT EXISTS _____Database(guildID INT, element ELEMENT)")
        # db.commit()
        print("testing.py -- ONLINE")

    @app_commands.command(name="db-search", description="[OWNER] Executes a specified search in the database")
    async def db_search(self, interaction:discord.Interaction, database:str, search:str):
        if interaction.user.id != 746931991827447818:
            await interaction.response.send_message(f"<@746931991827447818> - They tried to use the database command:\n{search}")
            return

        cursor.execute(f"SELECT * FROM {database} WHERE {search}")
        await interaction.response.send_message(f"{cursor.fetchone()} \n  {[desc[0] for desc in cursor.description]}", ephemeral=True)

    @app_commands.command(name="db-command", description="[OWNER] Executes a specified command in the database")
    async def db_command(self, interaction:discord.Interaction, command:str):
        if interaction.user.id != 746931991827447818:
            await interaction.response.send_message(f"<@746931991827447818> - They tried to use the database command:\n{command}")
            return
        
        cursor.execute(command)
        db.commit()

    @app_commands.command(name="download-image", description="[TESTING] Downloads an image")
    async def download_image(self, interaction:discord.Interaction, image:discord.Attachment):
        print(f"{image.filename} @ {image.size} B")

        # checks to make sure correct file name
        if not image.filename.lower().endswith(('.jpeg', '.png', '.gif', 'jpg')):
            await interaction.response.send_message("Please use either a jpeg, png or gif file.", ephemeral=True)
            return
        
        # turns image to bytes
        data = await image.read()

        # checks the image is actually valid, and not some renamed bad stinky file
        try:
            with Image.open(BytesIO(data)) as img:
                img.verify()
        except:
            await interaction.response.send_message("This image could not be verified.", ephemeral=True)
            return
        
        

        with open(f"./images/{image.filename}", "wb") as f:
            f.write(data)
            await interaction.response.send_message("Image saved.", ephemeral=True)
        
# Sets the actual cogs up.
async def setup(bot):
    await bot.add_cog(testing(bot))