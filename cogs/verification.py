import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"CREATE TABLE IF NOT EXISTS tagDatabase(guildID INT, tag STRING, tagUses INT, PRIMARY KEY (guildID, tag))")
        db.commit()
        print("verification.py -- ONLINE")


    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message is None: return
        if message.interaction_metadata: return
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'INTROS'",
                       (message.guild.id,))
        result = cursor.fetchone()
        if result[0] is None: return
        introChannel = message.guild.get_channel(result[0])

        if message.channel != introChannel: return 
        if message.author.bot: return

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'VERIFIED'", (message.guild.id,))
        verifRole = message.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (message.guild.id,))
        unverifRole = message.guild.get_role(cursor.fetchone()[0])

        await message.author.remove_roles(unverifRole)
        await message.author.add_roles(verifRole)


    # @app_commands.command(name="set-tags", description="[STAFF] - Sets the tags for the server, please use /setup-verification after it.")
    # @app_commands.checks.has_permissions(administrator = True)
    # @app_commands.describe(
    #     tags = "The tags for the server, seperated by comma and space. Eg. yuri, girls-kissing, wlw, roleplay-too-ig"
    # )
    # async def set_tags(self, interaction:discord.Interaction, tags: str):
    #     # Checks to see if one exists
    #     cursor.execute(f"SELECT purpose FROM administrationDatabase WHERE class = 'TAGS' AND guildID = ?",
    #                                        (interaction.guild.id,))
    #     tags = cursor.fetchone()

    #     if tags is None:
    #         cursor.execute(f"INSERT INTO administrationDatabase(guildID, class, classID, purpose) VALUES (?,?,?,?)",
    #                        (interaction.guild.id, 'TAGS', 0, tags))
    #     else:
    #         cursor.execute(f"UPDATE administrationDatabase SET purpose = ? WHERE guildID = ? AND class = ?",
    #                        (tags, interaction.guild.id, 'TAGS'))
    #     db.commit()

    #     # Logs the action
    #     await log_action(interaction, 2, "/set-tags",
    #                      f"<@{interaction.user.id}> has set the tags of the server to be: {tags}")

    #     # Confirms it's been updated.
    #     await interaction.response.send_message("Successfully updated the tags for the server.", ephemeral=True)
        

    

    # Sets up the verification system
    @app_commands.command(name="setup-verification", description="[STAFF] - Sends the verification system embed.")
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.describe(
        channel="The channel in which the buttons are being sent",
        )
    async def setup_verification(self, interaction:discord.Interaction, channel:discord.TextChannel):
        # Verification embed
        verification_embed = discord.Embed(
            title="Server Verification~",
            colour=discord.Colour.greyple(),
            description="To enter the server, we ask that you select which tag you used to join the server, just so we can tell"+
            " what tags work, and what tags don't! \n-# You can also check this information using /get-tag-stats.~"
        )
        await channel.send(embed=verification_embed, view=TagButtons())
        await interaction.response.send_message("The verification system has been successfully sent!", ephemeral=True)




    @app_commands.command(name="get-tag-stats", description="Returns the tag statistics for the server, who has used what tags and how many times.")
    async def get_tag_stats(self, interaction:discord.Interaction):
        cursor.execute("SELECT * FROM tagDatabase WHERE guildID = ?", (interaction.guild.id,))
        results = cursor.fetchall()

        embed = discord.Embed(
            title="Tag Statistics",
            description="The tag statistics for the server currently is:",
            colour= discord.Colour.brand_green()
        )

        for result in results:
            embed.description += f"\n**{result[1].lower()}** :: {result[2]}"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)




    # @app_commands.command(name="force-verify", description="Forces a verification to go through if the buttons have failed.")
    # @app_commands.describe(
    #     user="The user to be verified, anyone can use this command."
    # )
    # async def force_verify(self, interaction:discord.Interaction, user: discord.Member):
    #     # Verification Role logic
    #     cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'VERIFIED'", (interaction.guild.id,))
    #     verifRole = interaction.guild.get_role(cursor.fetchone()[0])
    #     cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
    #     unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

    #     await user.remove_roles(unverifRole)
    #     await user.add_roles(verifRole)

    #     # Sends confirmation
    #     await interaction.response.send_message("The user has been verified.", ephemeral=True)
    #     await log_action(interaction, interaction.user, 0, "/force-verify", "Forced Verification", user)






class TagButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        tags = ["roleplay", "fantasy", "fantasy-rp", "anime-rp", "yuri"]

        for tag in tags:
            button = discord.ui.Button(
                label=tag, custom_id=tag,
                style=discord.ButtonStyle.gray
            )
            button.callback = self.verification_button
            self.add_item(button)

        na_button = discord.ui.Button(
            label="N/A", custom_id="N/A",
            style=discord.ButtonStyle.danger)
        na_button.callback = self.na_button
        self.add_item(na_button)

        
    async def verification_button(self, interaction: discord.Interaction):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to an introductions channel, in which you can send an introduction, which will give you access to the rest of the server!''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, interaction.data["custom_id"]))
        result = cursor.fetchone()
        print(f"result = {result}")
        print(interaction.data["custom_id"])

        # Updating the database values
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id,interaction.data["custom_id"]))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, interaction.data["custom_id"]))
        db.commit()

        # Finding the relevant role IDs
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        try:
            verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        except:
            raise ValueError("There is no stage1 verification role set.")
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        try:
            unverifRole = interaction.guild.get_role(cursor.fetchone()[0])
        except:
            raise ValueError("There is no unverified role set.")

        # Adding and removing roles.
        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)


    # The N/A Button if they joined through another method
    async def na_button(self, interaction: discord.Interaction):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to an introductions channel, in which you can send an introduction, which will give you access to the rest of the server!''')

        # Finding the relevant role IDs
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        try:
            verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        except:
            raise ValueError("There is no stage1 verification role set.")
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        try:
            unverifRole = interaction.guild.get_role(cursor.fetchone()[0])
        except:
            raise ValueError("There is no unverified role set.")

        # Adding and removing roles.
        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)


async def setup(bot):
    await bot.add_cog(verification(bot))