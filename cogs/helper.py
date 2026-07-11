import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class helper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # db.execute(f"CREATE TABLE IF NOT EXISTS _____Database(guildID INT, element ELEMENT)")
        # db.commit()
        print("helper.py -- ONLINE")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (member.guild.id,))
        unverifRole = member.guild.get_role(cursor.fetchone()[0])

        await member.add_roles(unverifRole)
        
    @app_commands.command(name="send-faction-embed", description="[STAFF+] - Sends the faction embed to the specified channel")
    @app_commands.checks.has_permissions(manage_roles = True)
    @app_commands.describe(
        channel = "The channel where the embed will be sent",
        faction_name = "The name of the faction",
        faction_epoch = "The epoch which the faction is based in (N/A for neither)",
        faction_blurb = "The blurb written by the faction owner.",
        faction_link="A link to the faction post."
    )
    async def send_faction_embed(self, interaction:discord.Interaction, channel: discord.TextChannel, faction_name:str, faction_epoch:str, faction_blurb: str, faction_link: str):
        factionEmbed = discord.Embed(
            title = faction_name + " — " + faction_epoch,
            description=faction_blurb,
            url=faction_link
        )

        await channel.send(embed=factionEmbed)
        await interaction.response.send_message("Embed sent.", ephemeral=True)




    @app_commands.command(name="send-species-embed", description="[STAFF+] - Sends the species embed to the specified channel")
    @app_commands.checks.has_permissions(manage_roles = True)
    @app_commands.describe(
        channel = "The channel where the embed will be sent",
        species_name = "The name of the species.",
        species_blurb = "The blurb of the species written by the poster",
        species_link = "The link to the species post."
    )
    async def send_species_embed(self, interaction:discord.Interaction, channel: discord.TextChannel, species_name:str, species_blurb: str, species_link: str):
        speciesEmbed = discord.Embed(
            title = species_name,
            description=species_blurb,
            url=species_link
        )

        await channel.send(embed=speciesEmbed)
        await interaction.response.send_message("Embed sent.", ephemeral=True)

    
    @app_commands.command(name="delete-channels", description="[STAFF+] - Deletes the channel this message was sent in.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def delete_channel(self, interaction:discord.Interaction):
        await interaction.channel.delete();

        
        

async def setup(bot):
    await bot.add_cog(helper(bot))