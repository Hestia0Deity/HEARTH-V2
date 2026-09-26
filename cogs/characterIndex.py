import discord, sqlite3, os, dotenv, random, re
import sqlite3
from PIL import Image
from datetime import datetime
from io import BytesIO
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class characterIndex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Creating the database to contain all the additional muse information.
        db.execute(f"""CREATE TABLE IF NOT EXISTS museInfoDatabase(
                   guildID INT NOT NULL,
                   userID INT NOT NULL,
                   muse STRING NOT NULL,
                   age STRING, faction STRING, occupation STRING, rank STRING, arcane_level STRING, 
                   arcane_affiliation STRING, status STRING, partner STRING, sexuality STRING, avatarPath STRING, 
                   description STRING,
                   PRIMARY KEY (muse, userID, guildID)
                   FOREIGN KEY (muse, userID, guildID) REFERENCES museDatabase (muse, userID, guildID)
                   ON DELETE CASCADE ON UPDATE CASCADE)""")
        # Necessary to ensure that deletions are cascading, AKA when deleted from museDatabase
        # it'll also be deleted from museInfoDatabase
        db.execute(f"PRAGMA foreign_keys = ON")
        db.commit()

        # Adds all characters from the museDatabase into the museInfoDatbase
        cursor.execute(f"""INSERT OR IGNORE INTO museInfoDatabase (guildID, userID, muse)
        SELECT guildID, userID, muse FROM museDatabase""")
        db.commit()
        print("characterIndex.py -- ONLINE")



    
    # /search-muses
    @app_commands.command(name="search-muses", description="Searches the database for any muse with a matching name")
    @app_commands.describe(
        muse = "The name of the muse/character you're searching for",
        hidden = "Whether the response should be hidden or not (default = true)"
    )
    async def search_muses(self, interaction:discord.Interaction, muse: str, hidden: bool = True):
        # Gets the characters with similar names
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse LIKE ? COLLATE NOCASE",
                       (interaction.guild.id, f"%{muse}%"))
        result = cursor.fetchall()

        # If there are multiple results, sets a list of them which will be inserted into a dropdown
        if len(result) > 1:
            await interaction.response.send_message("The following results have been found, please pick the muse you wish to view.", view=SearchResults(result), ephemeral=hidden)
        elif result != []:
            cursor.execute("SELECT * FROM museInfoDatabase WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                       (interaction.guild.id, f"{muse}"))
            muse_info = cursor.fetchone()

            museEmbed, file = await get_character_embed(interaction, result[0], muse_info)
            if file is not None:
                await interaction.response.send_message(embed=museEmbed, ephemeral=hidden, file=file)
            else:
                await interaction.response.send_message(embed=museEmbed, ephemeral=hidden)
        else:
            await interaction.response.send_message("No character with that name could be found.", ephemeral=True)


    # /muse-index
    @app_commands.command(name="muse-index", description="Shows a list of a user's muses/characters.")
    @app_commands.describe(
        user = "The user who's index you want to check. (Default = you)",
        hidden = "Whether or not the visible should be only visible to you. (Default = True)"
    )
    async def muse_index(self, interaction:discord.Interaction, user:discord.User = None, hidden:bool = True):
        # Defers interaction
        await interaction.response.defer(ephemeral=hidden, thinking=True)
        
        # Sets the default user to the command author if it isn't already set.
        if user == None: user = interaction.user
        
        # Gets all the user's muses for this server.
        cursor.execute(f"SELECT * FROM museDatabase WHERE guildID = ? AND userID = ?",
                       (interaction.guild.id, user.id))
        muses = cursor.fetchall()
        muse_names = [muse[2] for muse in muses]

        if len(muses) == 0:
            await interaction.followup.send("This user has no characters.", ephemeral=True)
            return

        # Compiles the muses into an embed
        index_embed = discord.Embed(
            title=f"{user.global_name}'s Muse Index",
            description=f"This is an index of <@{user.id}>'s muses, with document messages hyperlinked.",
            colour=discord.Colour.orange(),
            timestamp=datetime.now()
        )
        index_embed.set_thumbnail(url=user.avatar.url)

        # Grabs the accepted characters channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                    (interaction.guild.id, "ACCEPTED"))
        accepted_channel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Creates a list of names, with document links hyperlinked.
        linked_names = []
        for muse in muses:
            linked_names.append(f"[{muse[2]}]({muse[5]})")

        # Dividing the linked names into three equal(ish) fields
        k, m = divmod(len(muse_names), 3)
        chunked_names = [
            linked_names[i*k + min(i, m):(i+1)*k + min(i+1, m)]
            for i in range(3)
        ]

        # Finally adding these names as fields to the embed
        for names in chunked_names:
            index_embed.add_field(name="‎", value="\n".join(names))

        await interaction.followup.send(embed=index_embed, ephemeral=hidden, view=SearchResults(muses))
    

    # /edit-profile
    @app_commands.command(name="edit-profile", description="Brings up a menu to edit a muse's profile.")
    @app_commands.describe(
        muse = "Name of the muse who's profile you want to edit."
    )
    async def edit_profile(self, interaction:discord.Interaction, muse:str):
        # Gets the characters with similar names
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND userID = ? AND muse LIKE ? COLLATE NOCASE",
                       (interaction.guild.id, interaction.user.id, f"%{muse}%"))
        muses = cursor.fetchall()

        # Muse count checks
        if len(muses) == 0:
            await interaction.response.send_message("No muses with that name could be found", ephemeral=True)
        elif len(muses) > 1:
            await interaction.response.send_message("There were multiple muses with that name, or similar names. Please pick the one you intended",
                                                    view=EditSearchResults(muses), ephemeral=True)
        else:            
            # Send the dropdown menu.
            cursor.execute(f"SELECT * FROM museDatabase JOIN museInfoDatabase USING (userID, guildID, muse) WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                           (interaction.guild.id, muse))
            muse_info = cursor.fetchone()
            await interaction.response.send_message("Please pick from the following values to edit.\n-# Name and faceclaim must be edited through /edit-muse instead.", 
                                                    view=EditOptions(muse_info), ephemeral=True)
            

    # /edit-muse
    @app_commands.command(name="edit-muse", description="Allows the name or faceclaim of the muse to be changed.")
    @app_commands.describe(
        muse= "The CURRENT name of the Muse you are editing",
        name = "The NEW name of the muse you are editing",
        faceclaim = "The NEW faceclaim of the muse you are editing"
    )
    async def edit_muse(self, interaction:discord.Interaction, muse: str, name: str = None, faceclaim: str = None):
        # Checks if they provided both as None.
        if name == None and faceclaim == None:
            await interaction.response.send_message("You did not provide anything to be changed???", ephemeral=True)
            return
        
        # Gets the existing muse information
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        muse_info = cursor.fetchone()

        # Checks if the person has the manage roles permission, or owns the muse.
        if muse_info[1] != interaction.user.id and not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("You do not own this muse.", ephemeral=True)

        # Edits the actual information.
        if name is not None and faceclaim is None:
            cursor.execute("UPDATE museDatabase SET muse = ? WHERE guildID = ? AND muse = ?",
                           (name, interaction.guild.id, muse))
            db.commit()

            await interaction.response.send_message("The Following actions were completed:\n"+
                                                    f"> - **Name:** {muse} → {name}",
                                                    ephemeral=True)
        elif name is None and faceclaim is not None:
            cursor.execute("UPDATE museDatabase SET faceclaim = ? WHERE guildID = ? AND muse = ?",
                           (faceclaim, interaction.guild.id, muse))
            db.commit()

            await interaction.response.send_message("The Following actions were completed:\n"+
                                                    f"> - **Faceclaim:** {muse_info[3]} → {faceclaim}",
                                                    ephemeral=True)
        elif name is not None and faceclaim is not None:
            cursor.execute("UPDATE museDatabase SET muse = ?, faceclaim = ? WHERE guildID = ? AND muse = ?",
                           (name, faceclaim, interaction.guild.id, muse))
            db.commit()

            await interaction.response.send_message("The Following actions were completed:\n"+
                                                    f"> - **Name:** {muse} → {name}\n" +
                                                    f"> - **Faceclaim:** {muse_info[3]} → {faceclaim}",
                                                    ephemeral=True)


    # /search-attribute
    @app_commands.command(name="search-attribute", description="Searches for any characters with the specified attribute.")
    @app_commands.describe(
        type = "The type of attribute to search",
        attribute = "The specified attribute you're searching",
        hidden = "Whether or not the message is hidden (default = True)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Age", value="age"),
        app_commands.Choice(name="Faction", value="faction"),
        app_commands.Choice(name="Occupation", value="occupation"),
        app_commands.Choice(name="Rank", value="rank"),
        app_commands.Choice(name="Arcane Level", value="arcane_level"),
        app_commands.Choice(name="Arcane Affiliation", value="arcane_affiliation"),
        app_commands.Choice(name="Romantic Status", value="status"),
        app_commands.Choice(name="Partner", value="partner"),
        app_commands.Choice(name="Sexuality", value="sexuality")
    ])
    async def search_attribute(self, interaction:discord.Interaction, type: app_commands.Choice[str], attribute: str, hidden: bool = True):
        # Finds all the muses with matching, or similar attributes.
        cursor.execute(f"SELECT muse, userID, {type.value} FROM museDatabase JOIN museInfoDatabase USING (guildID, userID, muse)" +
                       f"WHERE guildID = ? AND {type.value} LIKE ? COLLATE NOCASE", 
                       (interaction.guild.id, f"%{attribute}%"))
        muses = cursor.fetchall()

        # If there are no muses with that information
        if len(muses) == 0:
            await interaction.response.send_message("No muses could be found with that information", ephemeral=hidden)
            return
        
        # Compiles the string/list of muses.
        muse_list = ""
        for muse in muses:
            interaction.guild.get_member(muse[1])
            muse_list += f"- {muse[0]} - {muse[2]}\n"
        
        await interaction.response.send_message(f"{len(muses)} matching muses were found:\n-# *Query: {type.name} = {attribute}*\n\n" 
                                                + muse_list, ephemeral=hidden)


    # /save-avatar
    @app_commands.command(name="save-avatar", description="Saves an avatar for the specified muse.")
    @app_commands.describe(
        muse = "The name of the muse",
        avatar = "The image, preferrably square and no bigger than 300x300, otherwise it will be scaled down."
    )
    async def save_avatar(self, interaction:discord.Interaction, muse:str, avatar:discord.Attachment):        
        # Checking if the file ends with the correct types.
        if not avatar.filename.lower().endswith(('.jpeg', '.png', '.gif', 'jpg')):
            await interaction.response.send_message("Please use either a jpeg, png or gif file.", ephemeral=True)
            return
        
        # Verifying the image file itself.
        raw_image = await avatar.read()
        try:
            img = Image.open(BytesIO(raw_image))
            img.verify()
        except:
            await interaction.response.send_message("This image file could not be verified.", ephemeral=True)
            return
        
        # Checking and adjusting image size if necessary.
        img = Image.open(BytesIO(raw_image))
        if any([size > 1000 for size in img.size]):
            img.thumbnail((1000,1000), Image.Resampling.LANCZOS)


        # Getting muse information to check if they exist.
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        muse_info = cursor.fetchone()

        # Checking if the muse exists/could be found, and if user owns that muse.
        if muse_info is None:
            await interaction.response.send_message("Could not find a muse with that name.", ephemeral=True)
            return
        elif muse_info[1] != interaction.user.id:
            await interaction.response.send_message("You do not own this muse.", ephemeral=True)
            return
        
        # Getting current path for muse avatar.
        cursor.execute("SELECT avatarPath FROM museInfoDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        avatar_path = cursor.fetchone()[0]
        
        # Deleting old avatar.
        try: 
            os.remove(avatar_path)
        except:
            print(f"{datetime.now()} | Couldn't find the following avatar: {avatar_path}")
        
        # Making images directory (if necessary) and saving image 
        os.makedirs("./images", exist_ok=True)
        img_name = "./images/" + str(muse_info[1]) + "_" + muse.replace(" ", "-") + "." + img.format.lower()
        img.save(img_name)
        
        # Adding to database.
        cursor.execute("UPDATE museInfoDatabase SET avatarPath = ? WHERE guildID = ? AND muse = ?",
                       (img_name, interaction.guild.id, muse))
        db.commit()
        await interaction.response.send_message("Successfully saved the avatar.", ephemeral=True)


    # /delete-avatar
    @app_commands.command(name="delete-avatar", description="Deletes the current avatar for a muse.")
    @app_commands.describe(
        muse = "The name of the muse"
    )
    async def delete_avatar(self, interaction:discord.Interaction, muse:str):
        # Getting muse information to check if they exist.
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        muse_info = cursor.fetchone()

        # Checking if the muse exists/could be found.
        if muse_info is None:
            await interaction.response.send_message("Could not find a muse with that name.", ephemeral=True)
            return
        elif muse_info[1] != interaction.user.id:
            await interaction.response.send_message("You do not own this muse.", ephemeral=True)
            return
        
        # Getting current path for muse avatar.
        cursor.execute("SELECT avatarPath FROM museInfoDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, muse))
        avatar_path = cursor.fetchone()[0]
        
        # Deleting avatar.
        os.remove(avatar_path)

        # Removing reference to avatar path.
        cursor.execute("UPDATE museInfoDatabase SET avatarPath = ? WHERE guildID = ? AND muse = ?",
                       (None, interaction.guild.id, muse))
        await interaction.response.send_message("Successfully deleted that avatar.", ephemeral=True)




# Creates the embed from the retrived lists
async def get_character_embed(interaction: discord.Interaction, muse_list: list, info_list: list) -> discord.Embed:
    # Mapping for the embed information list.
    information_mapping = ["Age", "Faction", "Occupation", 
                       "Rank", "Arcane_Level", "Arcane_Affiliation",
                       "Status", "Partner", "Sexuality"]
    
    # Gets the accepted character link
    cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = ?",
                   (interaction.guild.id, "ACCEPTED"))
    channel = interaction.guild.get_channel(cursor.fetchone()[0])
    message = await channel.fetch_message(muse_list[4])
    link = re.search(r"\[.*?\]\((.*?)\)", message.content)
    
    # Creates the starting point for the embed
    embed = discord.Embed(
        title=muse_list[2], url=link.group(1) if link else None,
        description= f"This is a character owned by: <@{info_list[1]}>",
        colour= discord.Colour.orange(), timestamp = datetime.now()
    )
    if info_list[13] is not None: embed.description = embed.description + "\n\n" + info_list[13]

    # Sets the muse thumbnail to the muse's avatar.
    if info_list[12] is not None: 
        try:
            file = discord.File(info_list[12], filename=info_list[12].split("/")[-1])
            embed.set_thumbnail(url=f"attachment://{info_list[12].split('/')[-1]}")
        except:
            embed.set_thumbnail(url=interaction.guild.get_member(muse_list[1]).avatar.url)
            file = None
    else: 
        embed.set_thumbnail(url=interaction.guild.get_member(muse_list[1]).avatar.url)
        file = None

    # Adds the faceclaim field if it exists
    if muse_list[3] is not None:
        embed.add_field(name="Faceclaim", value=muse_list[3])

    # Adds a field for each NON-EMPTY field.
    info_list = info_list[3:11]
    for x, field in enumerate(info_list):
        if field is None: continue

        # Inline if even, otherwise not.
        embed.add_field(name=information_mapping[x], value=field, inline=True)
    
    return embed, file



# The list of muses, if there was multiple results.
class SearchResults(discord.ui.View):
    def __init__(self, characters: list):
        super().__init__(timeout=None)
        self.characters = characters
        self.searchResults = []
    
        for character in characters:
            self.searchResults.append(discord.SelectOption(label=character[2], value=character[2]))
        
        self.select_character.options = self.searchResults
    
    @discord.ui.select(placeholder="What character do you want to view?",
                       options=[],
                       max_values=1,
                       min_values=1)
    async def select_character(self, interaction:discord.Interaction, select_item: discord.ui.Select):
        cursor.execute("SELECT * FROM museDatabase WHERE guildID = ? AND muse = ?",
                       (interaction.guild.id, select_item.values[0]))
        muse_list = cursor.fetchone()

        cursor.execute("SELECT * FROM museInfoDatabase WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                       (interaction.guild.id, f"{muse_list[2]}"))
        muse_info = cursor.fetchone()

        museEmbed, file = await get_character_embed(interaction, muse_list, muse_info)
        if file is not None:
            await interaction.response.send_message(embed=museEmbed, ephemeral=True, file=file)
        else:
            await interaction.response.send_message(embed=museEmbed, ephemeral=True)




class EditSearchResults(discord.ui.View):
    def __init__(self, characters: list):
        super().__init__(timeout=None)
        self.characters = characters
        self.searchResults = []
    
        for character in characters:
            self.searchResults.append(discord.SelectOption(label=character[2], value=character[2]))
        
        self.select_character.options = self.searchResults
    
    @discord.ui.select(placeholder="What character do you want to edit?",
                       options=[],
                       max_values=1,
                       min_values=1)
    async def select_character(self, interaction:discord.Interaction, select_item: discord.ui.Select):
        # Getting the relevant muse information.
        cursor.execute(f"SELECT * FROM museDatabase JOIN museInfoDatabase USING (userID, guildID, muse) WHERE guildID = ? AND muse = ? COLLATE NOCASE",
                           (interaction.guild.id, select_item.values[0]))
        muse_info = cursor.fetchone()

        # Checks if they own the character.
        if muse_info[1] != interaction.user.id:
            await interaction.response.send_message("You do not own this muse.", ephemeral=True)
            return
        
        # Sending the modal.
        await interaction.response.send_message("Please pick from the following values to edit.\n-# Name and faceclaim must be edited through /edit-muse instead.", 
                                                    view=EditOptions(muse_info), ephemeral=True)
        

class EditOptions(discord.ui.View):
    def __init__(self, muse):
        super().__init__(timeout=None)
        self.muse = muse

    @discord.ui.select(
        placeholder="What options do you want to edit? (Max 5)",
        options=[
            discord.SelectOption(label="Age"),
            discord.SelectOption(label="Faction"),
            discord.SelectOption(label="Occupation"),
            discord.SelectOption(label="Rank"),
            discord.SelectOption(label="Arcane Level"),
            discord.SelectOption(label="Arcane Affiliation"),
            discord.SelectOption(label="Partner"),
            discord.SelectOption(label="Sexuality"),
            discord.SelectOption(label="Romantic Status"),
            discord.SelectOption(label="Description")
        ],
        min_values=1, max_values=5
        )
    async def select_options(self, interaction:discord.Interaction, select_item: discord.ui.Select):
        await interaction.response.send_modal(EditProfileModal(self.muse, self.select_options.values))


class EditProfileModal(discord.ui.Modal):
    def __init__(self, muse, values):
        super().__init__(title=f"Edit Profile - {muse[2]}", timeout=None)
        self.muse = muse
        self.inputs = []
        self.field_map = {
            "Age": 5,
            "Faction": 6,
            "Occupation": 7,
            "Rank": 8,
            "Arcane Level": 9,
            "Arcane Affiliation": 10,
            "Partner": 12,
            "Sexuality": 13,
            "Romantic Status": 11,
            "Profile Description": 15,
        }

        # Adding the relevant inputs
        for value in values:
            pos = self.field_map.get(value)

            # if it is an arcane level
            if pos == 9:
                item = discord.ui.Label(
                    text="Arcane Level",
                    component=discord.ui.Select(options=[
                        discord.SelectOption(label="Theios/Ascended Arcanist", value="Theios/Ascended Arcanist"),
                        discord.SelectOption(label="Megistos/High Arcanist", value="Megistos/High Arcanist"),
                        discord.SelectOption(label="Mesos/Medium Arcanist", value="Mesos/Medium Arcanist"),
                        discord.SelectOption(label="Elachistos/Low Arcanist", value="Elachistos/Low Arcanist")
                    ])
                )
            else:
                # every other type
                item = discord.ui.TextInput(
                    label=value,
                    default=muse[pos],
                    style= discord.TextStyle.short if pos != 15 else discord.TextStyle.paragraph,
                    required=False
                )

            self.inputs.append(item)
            self.add_item(item)

    async def on_submit(self, interaction:discord.Interaction):
        completed_log = ""

        for item in self.inputs:
            # Sets it to None so it actually appears as Null in the database.
            if item.value == "":
                value = None
            else:
                value = item.value
            
            # Updates the database.
            cursor.execute(f"UPDATE museInfoDatabase SET {(item.label.lower()).replace(' ', '_')} = ? WHERE guildID = ? AND muse = ?", 
                           (value,self.muse[0], self.muse[2]))
            completed_log += f"> - {item.label} → {value}\n"
        db.commit()

        await interaction.response.send_message("The following action(s) were completed:\n" + completed_log, ephemeral=True)

async def setup(bot):
    await bot.add_cog(characterIndex(bot))