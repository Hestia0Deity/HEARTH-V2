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

    

    # Sets up the verification system
    @app_commands.command(name="setup-verification", description="[STAFF] - Sets up the verification system for the server, adding tags and such")
    @app_commands.checks.has_permissions(administrator = True)
    @app_commands.describe(
        channel="The channel in which the buttons are being sent",
        message="The message to add to the buttons."
        )
    async def setup_verification(self, interaction:discord.Interaction, channel:discord.TextChannel, message:str):
        await channel.send(message, view=TagButtons())




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

    @discord.ui.button(label="roleplay",style=discord.ButtonStyle.gray, custom_id="roleplay")
    async def button1(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, self.button1.custom_id))
        result = cursor.fetchone()

        # Role logic
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id, self.button1.custom_id))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, self.button1.custom_id))
        db.commit()

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)


    @discord.ui.button(label="slice-of-life",style=discord.ButtonStyle.gray, custom_id="slice-of-life")
    async def button2(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, self.button2.custom_id))
        result = cursor.fetchone()

        # Role logic
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id, self.button2.custom_id))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, self.button2.custom_id))
        db.commit()

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)
    

    @discord.ui.button(label="yuri",style=discord.ButtonStyle.gray, custom_id="yuri")
    async def button3(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, self.button3.custom_id))
        result = cursor.fetchone()

        # Role logic
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id, self.button3.custom_id))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, self.button3.custom_id))
        db.commit()

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)
    

    @discord.ui.button(label="anime-rp",style=discord.ButtonStyle.gray, custom_id="anime-rp")
    async def button4(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, self.button4.custom_id))
        result = cursor.fetchone()

        # Role logic
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id, self.button4.custom_id))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, self.button4.custom_id))
        db.commit()

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)
    

    @discord.ui.button(label="arknights",style=discord.ButtonStyle.gray, custom_id="arknights")
    async def button5(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        #  Check if exists
        cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, self.button5.custom_id))
        result = cursor.fetchone()

        # Role logic
        cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
                        (interaction.guild.id, self.button5.custom_id))
        if result is not None:
            cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
                        (result[0]+1, interaction.guild.id, self.button5.custom_id))
        db.commit()

        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)


    @discord.ui.button(label="n/a",style=discord.ButtonStyle.red, custom_id="n/a")
    async def button6(self, interaction: discord.Interaction, Button: discord.ui.Button):
        # Sends a confirmation message
        await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        await interaction.user.send('''Thank you for verifying! You should now have access to <#1460101223695908879>, in which you can send an introduction, which will give you access to the rest of the server!\n-# You can find the introduction template [here](https://canary.discord.com/channels/1460101221036720180/1460101223695908879/1460439147121742100).''')
        
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED_TWO'", (interaction.guild.id,))
        verifRole = interaction.guild.get_role(cursor.fetchone()[0])
        cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
        unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

        await interaction.user.remove_roles(unverifRole)
        await interaction.user.add_roles(verifRole)



# class TagButtons(discord.ui.View):
#     def __init__(self, tags: list[str]):
#         super().__init__(timeout=None)
#         self.tags = tags

#         for tag in tags:
#             button = discord.ui.Button(
#                 label=tag,
#                 style = discord.ButtonStyle.blurple,
#                 custom_id=tag
#             )
#             button.callback = self.make_callback(tag)
#             self.add_item(button)

#         noneButton = discord.ui.Button(
#             label="N/A",
#             style = discord.ButtonStyle.red,
#             custom_id="N/A"
#         )
#         noneButton.callback = self.none_callback
#         self.add_item(noneButton)

#     def make_callback(self, tag: str):
#         async def callback(interaction: discord.Interaction):
#             # Check if exists
#             cursor.execute(f"SELECT tagUses FROM tagDatabase WHERE guildID = ? AND tag = ?",(interaction.guild.id, tag))
#             result = cursor.fetchone()


#             # Sends confirmation message
#             await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)


#             # Role logic
#             cursor.execute("INSERT OR IGNORE INTO tagDatabase(guildID, tag, tagUses) VALUES (?, ?, 1)",
#                            (interaction.guild.id, tag))
#             if result is not None:
#                 cursor.execute("UPDATE tagDatabase SET tagUses = ? WHERE guildID = ? AND tag = ?",
#                             (result[0]+1, interaction.guild.id, tag))
#             db.commit()


#             # Verification Role 
#             cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'VERIFIED'", (interaction.guild.id,))
#             verifRole = interaction.guild.get_role(cursor.fetchone()[0])
#             cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
#             unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

#             await interaction.user.remove_roles(unverifRole)
#             await interaction.user.add_roles(verifRole)


#         return callback
    
#     async def none_callback(self, interaction: discord.Interaction):
#         # Verification Role
#         cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'VERIFIED'", (interaction.guild.id,))
#         verifRole = interaction.guild.get_role(cursor.fetchone()[0])
#         cursor.execute(f"SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'UNVERIFIED'", (interaction.guild.id,))
#         unverifRole = interaction.guild.get_role(cursor.fetchone()[0])

#         await interaction.user.remove_roles(unverifRole)
#         await interaction.user.add_roles(verifRole)

#         # Sends confirmation message
#         await interaction.response.send_message("Verification complete, thank you!", ephemeral=True)
        





        

async def setup(bot):
    await bot.add_cog(verification(bot))