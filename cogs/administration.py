import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class administration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"""CREATE TABLE IF NOT EXISTS administrationDatabase(
                   guildID INT NOT NULL, 
                   class STRING NOT NULL,
                   classID INT NOT NULL,
                   purpose STRING NOT NULL,
                   PRIMARY KEY (guildID, classID, purpose)
                   )""")
        db.commit()
        print("administration.py -- ONLINE")




    # Sets the channel
    @app_commands.command(name="set-channel", description="[STAFF] - Sets the channel for the bot to utilise, such as where to send accepted character links.")
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Action Log", value="LOGS"),
        app_commands.Choice(name="Accepted Muses",value="ACCEPTED"),
        app_commands.Choice(name="Muse Submissions",value="SUBMISSIONS"),
        app_commands.Choice(name="Muse Management",value="MANAGEMENT"),
        app_commands.Choice(name="Muse Reviews",value="REVIEWS"),
        app_commands.Choice(name="Introductions Channel", value="INTROS"),
        app_commands.Choice(name="Reservations Channel", value="RESERVATIONS")
    ])
    @app_commands.describe(
        type="The type of channel to be updated",
        channel="The channel which it is being set to."
    )
    async def set_channel(self, interaction:discord.Interaction, type: app_commands.Choice[str], channel:discord.TextChannel):
        # checks to see if entry exists
        cursor.execute(f"""SELECT * FROM administrationDatabase WHERE guildID = {interaction.guild.id} AND purpose = '{type.value}'""")
        result = cursor.fetchone()


        # either updates an existing entry, or inserts a new one
        if result is None:
            cursor.execute(f"INSERT INTO administrationDatabase(guildID, class, classID, purpose) VALUES (?,?,?,?)",
                           (interaction.guild.id, 'CHANNEL', channel.id, type.value))
            db.commit()
            await interaction.response.send_message("The channel has been set.", ephemeral=True)
        else:
            cursor.execute(f"UPDATE administrationDatabase SET classID = ? WHERE guildID = {interaction.guild.id} AND purpose = '{type.value}'",
                           (channel.id,))
            db.commit()
            await interaction.response.send_message("The channel has been updated.", ephemeral=True)

        # logs the action
        await log_action(interaction, 1, "/set-channel", f"Updated Channel - {type.name}")




    # Sets a role
    @app_commands.command(name="set-role", description="[STAFF] - Sets a role for the bot to use, such as which role to give to those who own characters.")
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.choices(type=[
        app_commands.Choice(name="Verified Role", value="VERIFIED"),
        app_commands.Choice(name="Unverified Role 1", value="UNVERIFIED"),
        app_commands.Choice(name="Unverified Role 2", value="UNVERIFIED_TWO"),
        app_commands.Choice(name="Verified Muse Role", value="MUSE")
    ])
    @app_commands.describe(
        type="The type of role to be updated",
        role="The role which it is being set to."
    )
    async def set_role(self, interaction:discord.Interaction, type: app_commands.Choice[str], role:discord.Role):
        # checks to see if entry exists
        cursor.execute(f"""SELECT * FROM administrationDatabase WHERE guildID = {interaction.guild.id} AND purpose = '{type.value}'""")
        result = cursor.fetchone()

        # either inserts a new entry, or updates an existing one
        if result is None:
            cursor.execute(f"INSERT INTO administrationDatabase(guildID, class, classID, purpose) VALUES (?,?,?,?)",
                           (interaction.guild.id, 'ROLE', role.id, type.value))
            db.commit()
            await interaction.response.send_message("The role has been set.", ephemeral=True)
        else:
            cursor.execute(f"UPDATE administrationDatabase SET classID = ? WHERE guildID = {interaction.guild.id} AND purpose = '{type.value}'",
                           (role.id,))
            db.commit()
            await interaction.response.send_message("The role has been updated.", ephemeral=True)

        # logs the action
        await log_action(interaction, 1, "/set-role", f"Updated Role - {type.name}")




# Logs any action, getting 
async def log_action(interaction:discord.Interaction, severity:int, command:str, description:str):
    # Setting up the embed for the log
    logEmbed = discord.Embed(
        title=command,
        description=description,
        timestamp=datetime.now(),
    )
    logEmbed.set_author(name=interaction.user.global_name, icon_url=interaction.user.avatar.url)
    if severity == 0: logEmbed.colour = discord.Colour.brand_green()
    elif severity == 1: logEmbed.colour = discord.Colour.orange()
    else: logEmbed.colour = discord.Colour.brand_red()

    # Getting the action log channel
    cursor.execute(f"""SELECT classID FROM administrationDatabase 
                   WHERE guildID = {interaction.guild.id}
                   AND class = 'CHANNEL'
                   AND purpose = 'LOGS'""")
    logChannel = cursor.fetchone()


    # sends the log
    if logChannel is not None:
        logChannel = interaction.guild.get_channel(logChannel[0])
        await logChannel.send(embed=logEmbed)
    else:
        print(f"{interaction.user.id}, {datetime.now}, {command}\n" + description)

    
    

async def setup(bot):
    await bot.add_cog(administration(bot))