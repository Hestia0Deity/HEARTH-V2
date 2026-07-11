import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class submissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 
    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"""CREATE TABLE IF NOT EXISTS museDatabase(
                   guildID INT NOT NULL,
                   userID INT NOT NULL,
                   muse STRING NOT NULL,
                   faceclaim STRING NULL,
                   acceptedID INT NOT NULL,
                   PRIMARY KEY (muse, acceptedID, guildID),
                   UNIQUE (muse, userID, guildID))""")
        # Trigger to auto-insert into the museInfoDatabase whenever something is added in here.
        db.execute(f"""
                   CREATE TRIGGER IF NOT EXISTS museInfo_autoInsert
                   AFTER INSERT ON museDatabase
                   BEGIN
                       INSERT INTO museInfoDatabase(guildID, userID, muse)
                       VALUES (NEW.guildID, NEW.userID, NEW.muse);
                   END
                   """)
        db.commit()
        
        print("submissions.py -- ONLINE")

    
    # Add muse command
    @app_commands.command(name="add-muse", description="[STAFF] Adds a muse to the specified user, sending their link")
    @app_commands.checks.has_permissions(manage_roles = True)
    @app_commands.describe(
        name = "The name of the muse",
        user = "The user the muse belongs to",
        document_link = "The link to the muse's document",
        faceclaim = "The faceclaim used by the muse."
    )
    async def add_muse(self, interaction:discord.Interaction, name: str, user:discord.User, document_link:str, 
                       faceclaim:str = None):
        # Check if a character already exists with that name
        cursor.execute("SELECT muse FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, name))
        result = cursor.fetchone()
        if result is not None: 
            await interaction.response.send_message("A muse with this name already exists", ephemeral=True)
            return
        
        # Grabs the Accepted Muse channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "ACCEPTED"))
        accepted_channel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Sends the link/accepted message
        try:
            accepted_message = await accepted_channel.send(f"[**{name}**]({document_link}) — <@{user.id}>")
        except:
            await interaction.response.send_message("The muse message could not be send for some reason.", 
                                                    ephemeral=True)
            return

        # Adds the character to the database
        try:
            await addCharacter(interaction, name, user, accepted_message.id, faceclaim)
        except:
            await interaction.response.send_message("The character could not be added to the database",
                                                    ephemeral=True)
            await accepted_message.delete()
            return

        # Command response & logging
        await interaction.response.send_message("Muse successfully added.", ephemeral=True)
        await log_action(interaction, 2, "/add-muse",
                         f"<@{interaction.user.id}> has manually added the muse " +
                        f"**{name}**, owned by <@{user.id}>")
        

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message is None: return
        if message.interaction_metadata: return
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'SUBMISSIONS'",
                       (message.guild.id,))
        submissionChannel = message.guild.get_channel(cursor.fetchone()[0])
        
        if message.channel.id != submissionChannel.id: return
        if message.author.bot: return
        if "https://" not in message.content: return
        if not any(word in message.content for word in ["docs.google.com", "carrd.co"]): return

        subEmbed = discord.Embed(colour=discord.Colour.brand_green(), 
                              title="Thanks for submitting your muse~!", 
                              description="""Our staff will review it shortly, in the meantime please make sure you have read over it and ensured that it has the required information.
                              
                              If you have any questions, feel free to ask a staff member! And if its been more than 48 hours, you can ping a member of staff as well.
                              *The below buttons are for the usage of staff only, you can press them if you want! It just won't do anything.*""",
                              timestamp=datetime.now())
        subEmbed.set_footer(text=str(message.author.id)+"|"+str(message.id))
        await message.channel.send(embed=subEmbed, view=submissionButtons())
        



class submissionButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    ## Accept Button
    @discord.ui.button(label="Accept Submission",style=discord.ButtonStyle.green, custom_id="accept")
    async def accept(self, interaction: discord.Interaction, Button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_roles == True:
            await interaction.response.send_modal(AcceptanceModal())
        else:
            await interaction.response.send_message("You do not have the Manage Roles permission, as such cannot accept/deny applications.", ephemeral=True)
    
    
    ## Deny Button
    @discord.ui.button(label="Deny Submission",style=discord.ButtonStyle.red, custom_id="deny")
    async def deny(self, interaction: discord.Interaction, Button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_roles == True:
            await interaction.response.send_modal(DenialModal())
        else:
            await interaction.response.send_message("You do not have the Manage Roles permission, as such cannot accept/deny applications.", ephemeral=True)


## Modal sent when accepting a character
class AcceptanceModal(discord.ui.Modal, title="Acceptance Modal"):
    name = discord.ui.TextInput(label="Name", style=discord.TextStyle.short, required=True)
    faceclaim = discord.ui.TextInput(label="Faceclaim", style=discord.TextStyle.short, required=False, placeholder="Leave blank if none.")
    
    async def on_submit(self, interaction: discord.Interaction):
        ## Gets the accepted characters channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "ACCEPTED"))
        accepted_channel = interaction.guild.get_channel(cursor.fetchone()[0])

        ## DB Check
        cursor.execute("SELECT muse FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, self.name.value))
        result = cursor.fetchone()
        if result is not None: await interaction.response.send_message("A character with this name already exists", ephemeral=True); return

        ## Sending accepted message
        originalMessage = await interaction.channel.fetch_message(interaction.message.embeds[0].footer.text.split("|")[1])
        userID = int(interaction.message.embeds[0].footer.text.split("|")[0])
        user = interaction.guild.get_member(userID)
        submissionLink = re.findall(r'(https?://\S+)',originalMessage.content)
        acceptedMessage = await accepted_channel.send(f"**[{self.name.value}]({submissionLink[0]})** — <@{user.id}>")

        ## Adding to database
        if self.faceclaim.value != "": await addCharacter(interaction, self.name.value, user, acceptedMessage.id, self.faceclaim.value)
        else: await addCharacter(interaction, self.name.value, user, acceptedMessage.id)
        await log_action(interaction, 1, "Accepted a Character", f"<@{interaction.user.id}> " +
                         f"has accepted the character {self.name.value}.")

        ## Deleting old messages
        await interaction.response.send_message("Character accepted successfully", ephemeral=True)
        await interaction.message.delete()
        await originalMessage.delete()

        ## Giving the user the roleplayer role
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "MUSE"))
        verified_muse = interaction.guild.get_role(cursor.fetchone()[0])

        await user.add_roles(verified_muse)




## Modal sent when denying a character
class DenialModal(discord.ui.Modal, title="Acceptance Modal"):
    name = discord.ui.TextInput(label="Name", style=discord.TextStyle.short, required=True)
    denial_reason = discord.ui.TextInput(label="Reason for Denial", style=discord.TextStyle.paragraph, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        ## Gets the accepted characters channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "REVIEWS"))
        reviewChannel = interaction.guild.get_channel(cursor.fetchone()[0])

        ## Sending denial message
        originalMessage = await interaction.channel.fetch_message(interaction.message.embeds[0].footer.text.split("|")[1])
        userID = int(interaction.message.embeds[0].footer.text.split("|")[0])
        user = interaction.guild.get_member(userID)

        await reviewChannel.send(f"<@{userID}>, your character ({self.name.value}) has been denied. The following reasons were listed as for why:\n>>> " + self.denial_reason.value)

        ## Logging Action
        await log_action(interaction, 1, "Accepted a Character", f"<@{interaction.user.id}> " +
                         f"has denied the character {self.name.value}.")

        ## Deleting old messages
        await interaction.response.send_message("Character denied successfully", ephemeral=True)
        await interaction.message.delete()
        await originalMessage.delete()


# Add character function
async def addCharacter(interaction:discord.Interaction, character: str, user: discord.User, acceptedID: str, faceclaim: str = None):
    try:
        if faceclaim is not None:
            db.execute("INSERT INTO museDatabase(guildID, userID, muse, faceclaim, acceptedID) VALUES (?,?,?,?,?)",
                    (interaction.guild.id, user.id, character, faceclaim, int(acceptedID)))
        else:
            db.execute("INSERT INTO museDatabase(guildID, userID, muse, acceptedID) VALUES (?,?,?,?)",
                    (interaction.guild.id, user.id, character, int(acceptedID)))
    except:
        print("Character could not be added to the database")
        db.rollback()
        raise ValueError("Could not add to database.")
    db.commit()


async def setup(bot):
    await bot.add_cog(submissions(bot))