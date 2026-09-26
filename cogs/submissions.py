from discord.utils import MISSING
import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action

# Essential Variabes
dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()

# Miscellaneous Variables
submission_embed = discord.Embed(colour=discord.Colour.brand_green(), 
                                      title="Thanks for submitting your muse~!", 
                                      description="""Our staff will review it shortly, in the meantime please make sure you have read over it and ensured that it has the required information.
                                      
                                      If you have any questions, feel free to ask a staff member! And if its been more than 48 hours, you can ping a member of staff as well.
                                      *The below buttons are for the usage of staff only, you can press them if you want! It just won't do anything.~*""",
                                      timestamp=datetime.now())


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
                   document STRING NOT NULL,
                   PRIMARY KEY (muse, acceptedID, guildID),
                   UNIQUE (muse, userID, guildID),
                   UNIQUE (muse, guildID))""")
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
        db.execute(f"PRAGMA foreign_keys = ON")
        
        print("submissions.py -- ONLINE")

    
    # /add-muse
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
            await addCharacter(interaction, name, user, accepted_message.id, faceclaim, document_link)
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


    # /delete-muse
    @app_commands.command(name="delete-muse", description="Deletes the specified muse.")
    @app_commands.describe(
        muse = "The name of the muse to be deleted, needs to be exact."
    )
    async def delete_muse(self, interaction:discord.Interaction, muse:str):
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                       (interaction.guild.id, muse))
        muse_result = cursor.fetchone()

        # Checks if the muse even exists
        if muse_result is None: 
            await interaction.response.send_message(f"Could not find the muse {muse}, please try again.", ephemeral=True)
            return
        # Checks if the muse is not the user, and if they don't have delete permissions
        elif muse_result[1] != interaction.user.id and not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(f"You do not own the muse {muse}.", ephemeral=True)
        
        # Deletes the muse
        cursor.execute("DELETE FROM museDatabase WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                       (interaction.guild.id, muse))
        db.commit()

        # Deleting the accepted message link, if it exists
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "ACCEPTED"))
        accepted_channel = interaction.guild.get_channel(cursor.fetchone()[0])

        try:
            accepted_message = await accepted_channel.fetch_message(muse_result[4])
            await accepted_message.delete()
        except:
            print(f"{datetime.now()} | Could not delete the accepted message of {muse}")

        # Final response and logging.
        await interaction.response.send_message("The following changes have been made:\n"
                                                +f"-# *{muse} → DELETED*", ephemeral=True)
        await log_action(interaction, 3, "/delete-muse", 
                         f"<@{interaction.user.id}> has deleted the character "+
                         f"{muse}, owned by <@{muse_result[1]}>")
            


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

        subEmbed = submission_embed.copy()
        subEmbed.set_footer(text=str(message.author.id)+"|"+str(message.id))
        await message.channel.send(embed=subEmbed, view=submission_buttons())
        



class submission_buttons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Accept Button
    @discord.ui.button(label="Accept Submission",style=discord.ButtonStyle.green, custom_id="accept")
    async def accept(self, interaction: discord.Interaction, Button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_roles == True:
            await interaction.response.send_modal(AcceptanceModal())
        else:
            await interaction.response.send_message("You do not have the Manage Roles permission, as such cannot accept/deny applications.", ephemeral=True)
    
    
    # Deny Button
    @discord.ui.button(label="Deny Submission",style=discord.ButtonStyle.red, custom_id="deny")
    async def deny(self, interaction: discord.Interaction, Button: discord.ui.Button):
        if interaction.user.guild_permissions.manage_roles == True:
            await interaction.response.send_modal(DenialModal(interaction.message))
        else:
            await interaction.response.send_message("You do not have the Manage Roles permission, as such cannot accept/deny applications.", ephemeral=True)


    # Claim Button
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.gray, custom_id="claim")
    async def claim(self, interaction:discord.Interaction, button: discord.ui.Button):
        # Checks that the user is a staff member
        if not interaction.user.guild_permissions.manage_roles:
            interaction.response.send_message("You do not have the manage roles permission, hence cannot review muses.~", ephemeral=True)
            return
        
        # Deletes the claim button
        self.remove_item(button)

        # Edits the message to display which admin is handling the submission
        claimed_embed = submission_embed.copy()
        claimed_embed.description += f"\n\n **Your submission will be handled by:** <@{interaction.user.id}>"
        claimed_embed.footer = interaction.message.embeds[0].footer.text
        await interaction.message.edit(embed=claimed_embed, view=self)

        # Confirms with the admin
        await interaction.response.send_message("You have claimed this submission!", ephemeral=True)


# Modal sent when accepting a character
class AcceptanceModal(discord.ui.Modal, title="Acceptance Modal"):
    name = discord.ui.TextInput(label="Name", style=discord.TextStyle.short, required=True)
    faceclaim = discord.ui.TextInput(label="Faceclaim", style=discord.TextStyle.short, required=False, placeholder="Leave blank if none.")
    
    async def on_submit(self, interaction: discord.Interaction):
        # Gets the accepted characters channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "ACCEPTED"))
        accepted_channel = interaction.guild.get_channel(cursor.fetchone()[0])

        # DB Check
        cursor.execute("SELECT muse FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, self.name.value))
        result = cursor.fetchone()
        if result is not None: await interaction.response.send_message("A character with this name already exists", ephemeral=True); return

        # Sending accepted message
        originalMessage = await interaction.channel.fetch_message(interaction.message.embeds[0].footer.text.split("|")[1])
        userID = int(interaction.message.embeds[0].footer.text.split("|")[0])
        user = interaction.guild.get_member(userID)
        submissionLink = re.findall(r'(https?://\S+)',originalMessage.content)
        acceptedMessage = await accepted_channel.send(f"**[{self.name.value}]({submissionLink[0]})** — <@{user.id}>", silent=True)

        # Adding to database
        if self.faceclaim.value != "": await addCharacter(interaction, self.name.value, user, acceptedMessage.id, self.faceclaim.value, submissionLink[0])
        else: await addCharacter(interaction, self.name.value, user, acceptedMessage.id, None, submissionLink[0])
        await log_action(interaction, 1, "Accepted a Character", f"<@{interaction.user.id}> " +
                         f"has accepted the character {self.name.value}.")

        # Deleting old messages
        await interaction.response.send_message("Character accepted successfully", ephemeral=True)
        await interaction.message.delete()
        await originalMessage.delete()

        # Giving the user the roleplayer role
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "MUSE"))
        verified_muse = interaction.guild.get_role(cursor.fetchone()[0])

        await user.add_roles(verified_muse)

        # Grabs the review channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                            (interaction.guild.id, "REVIEWS"))
        reviewChannel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Sends a message in the review channel
        accepted_embed = discord.Embed(
            title=f"{self.name.value} has been accepted!",
            description="""Now that your muse has been accepted, you can edit/verify the major aspects of their profile through the below embed.
            
            If you want to edit further information, or if the button no longer works, you can do so with the `/edit-profile muse:[muse]` command!""",
        )
        await reviewChannel.send(f"-# <@{userID}>", embed=accepted_embed, view=edit_profile())


# Modal sent when denying a character
class DenialModal(discord.ui.Modal, title="Acceptance Modal"):
    name = discord.ui.TextInput(label="Name", style=discord.TextStyle.short, required=True)
    denial_reason = discord.ui.TextInput(label="Reason for Denial", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, message):
        super().__init__(timeout = None)
        self.message = message

    
    async def on_submit(self, interaction: discord.Interaction):
        # Gets the reviews channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "REVIEWS"))
        reviewChannel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Sending denial message
        originalMessage = await interaction.channel.fetch_message(self.message.embeds[0].footer.text.split("|")[1])
        userID = userID = int(self.message.embeds[0].footer.text.split("|")[0])

        await reviewChannel.send(f"<@{userID}>, your character ({self.name.value}) has been denied. The following reasons were listed as for why:\n>>> " + self.denial_reason.value)

        # Logging Action
        await log_action(interaction, 1, "Denied a Character", f"<@{interaction.user.id}> " +
                         f"has denied the character {self.name.value}.")

        # Deleting old messages
        await interaction.response.send_message("Character denied successfully", ephemeral=True)
        await interaction.message.delete()
        await originalMessage.delete()




# Button to edit a profile
class edit_profile(discord.ui.View):
    # Initialising variables 
    def __init__(self):
        super().__init__(timeout=86400)

    # Edit profile button
    @discord.ui.button(label="Edit Profile", style=discord.ButtonStyle.blurple, custom_id="edit")
    async def edit(self, interaction:discord.Interaction, button:discord.Button):
        # Gets the muse name
        muse = interaction.message.embeds[0].title.split(" has ")[0]

        # Checks if the interactor owns the muse
        cursor.execute("SELECT userID, muse, faceclaim FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        result = cursor.fetchone()

        # Checks if there was any result
        if result is None:
            await interaction.response.send_message("Something has gone wrong, and I could not find a muse with that name.", ephemeral=True)
            return
        
        # Checks if the user owns the muse
        if result[0] != interaction.user.id:
            await interaction.response.send_message("You do not own this muse.", ephemeral=True)
            return

        # Sends the modal
        await interaction.response.send_modal(EditProfileModal(result[1], result[2]))


# Modal to edit the profile
class EditProfileModal(discord.ui.Modal):
    # Initialising variables
    def __init__(self, muse, faceclaim):
        super().__init__(title=f"Edit Profile - {muse}", timeout=None)
        self.muse = muse
        self.faceclaim = faceclaim

        # Fields
        self.name = discord.ui.TextInput(label="Muse Name", style=discord.TextStyle.short, default=self.muse, required=False)
        self.faceclaim = discord.ui.TextInput(label="Muse Faceclaim", style=discord.TextStyle.short, default=self.faceclaim, required=False)
        self.faction = discord.ui.TextInput(label="Faction", style=discord.TextStyle.short, required=False)
        self.sexuality = discord.ui.TextInput(label="Sexuality", style=discord.TextStyle.short, required=False)
        self.muse_profile = discord.ui.TextInput(label="Muse Profile", style=discord.TextStyle.paragraph, placeholder="A summary of your muse for others to see. As little or as much info as you want.", required=False)

        ## Adding the items
        self.add_item(self.name)
        self.add_item(self.faceclaim)
        self.add_item(self.faction)
        self.add_item(self.sexuality)
        self.add_item(self.muse_profile)

    async def on_submit(self, interaction:discord.Interaction):
        # Checks if a muse already uses that name
        if self.name.value != self.muse:
            cursor.execute(f"SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?",
                        (self.name.value, interaction.guild.id))
            if cursor.fetchone() is not None:
                await interaction.response.send_message("A muse with that name already exists.", ephemeral=True)
                return

        # A log of completed/changed variables
        completed_log = ""

        
        if self.name.value == self.muse: name = self.muse
        else: name = self.name.value; completed_log += f"> - Muse Name → {self.name.value}\n"
        
        if self.faceclaim.value == "": faceclaim = None
        else: faceclaim = self.name.value; completed_log += f"> - Faceclaim → {self.faceclaim.value}\n"

        if self.faction.value == "": faction = None
        else: faction = self.faction.value; completed_log += f"> - Faction → {self.faction.value}\n"
        
        if self.sexuality.value == "": sexuality = None
        else: sexuality = self.sexuality.value; completed_log += f"> - Sexuality → {self.sexuality.value}\n"

        if self.muse_profile.value == "": profile = None
        else: profile = self.muse_profile.value; completed_log += f"> - Profile → Use `/search-muses` to find the profile."

        # Updating database
        cursor.execute(f"UPDATE museDatabase SET muse = ?, faceclaim = ? WHERE guildID = ? AND muse = ?",
                       (name, faceclaim, interaction.guild.id, self.muse))
        db.commit()
        cursor.execute(f"UPDATE museInfoDatabase SET faction = ?, sexuality = ?, description = ? WHERE guildID = ? AND muse = ?", 
                       (faction, sexuality, profile, interaction.guild.id, self.name.value))
        db.commit()

        await interaction.response.send_message("The following fields were set:\n" + completed_log, ephemeral=True)

        # Changes the name
        if self.name.value != self.muse:
            # Edits the accepted embed
            accepted_embed = discord.Embed(
                        title=f"{self.name.value} has been accepted!",
                        description="""Now that your muse has been accepted, you can edit/verify the major aspects of their profile through the below embed.
                        
                        If you want to edit further information, you can do so with the `/edit-profile muse:[muse]` command!""",
                    )
            
            await interaction.message.edit()

    


# Add character function
async def addCharacter(interaction:discord.Interaction, character: str, user: discord.User, acceptedID: str, faceclaim: str = None, document: str = None):
    try:
        if faceclaim is not None:
            db.execute("INSERT INTO museDatabase(guildID, userID, muse, faceclaim, acceptedID, document) VALUES (?,?,?,?,?,?)",
                    (interaction.guild.id, user.id, character, faceclaim, int(acceptedID), document))
        else:
            db.execute("INSERT INTO museDatabase(guildID, userID, muse, acceptedID, document) VALUES (?,?,?,?,?)",
                    (interaction.guild.id, user.id, character, int(acceptedID), document))
    except:
        print("Character could not be added to the database")
        db.rollback()
        raise ValueError("Could not add to database.")
    db.commit()


async def setup(bot):
    await bot.add_cog(submissions(bot))