import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
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
                   age STRING, rank STRING, position STRING, department STRING, division STRING, 
                   platoon STRING, status STRING, partner STRING, sexuality STRING, avatarPath STRING, 
                   description STRING,
                   PRIMARY KEY (muse, userID, guildID)
                   FOREIGN KEY (muse, userID, guildID) REFERENCES museDatabase (muse, userID, guildID)
                   ON DELETE CASCADE)""")
        # Necessary to ensure that deletions are cascading, AKA when deleted from museDatabase
        # it'll also be deleted from museInfoDatabase
        db.execute(f"PRAGMA foreign_keys = ON")
        db.commit()
        print("characterIndex.py -- ONLINE")


    # /search-muses - Searches the database for any muse with a matching name
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


    # /delete-muse - Deletes the muse if they either own it, or have the manage roles permission.
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
        

    @app_commands.command(name="muse-index", description="Shows a list of a user's muses/characters.")
    @app_commands.describe(
        user = "The user who's index you want to check. (Default = you)",
        hidden = "Whether or not the visible should be only visible to you. (Default = True)"
    )
    async def muse_index(self, interaction:discord.Interaction, user:discord.User = None, hidden:bool = True):
        # Sets the default user to the command author if it isn't already set.
        if user == None: user = interaction.user
        
        # Gets all the user's muses for this server.
        cursor.execute(f"SELECT * FROM museDatabase WHERE guildID = ? AND userID = ?",
                       (interaction.guild.id, user.id))
        muses = cursor.fetchall()
        muse_names = [muse[2] for muse in muses]

        if len(muses) == 0:
            await interaction.response.send_message("This user has no characters.", ephemeral=True)
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
            try:
                accepted_message = await accepted_channel.fetch_message(muse[4])
                linked_names.append(f"[{muse[2]}](" +
                    re.search(r"\((https:\/\/[^)]*)\)", accepted_message.content).group(1) + ")")
            except:
                linked_names.append(muse[2])

        # Dividing the linked names into three equal(ish) fields
        k, m = divmod(len(muse_names), 3)
        chunked_names = [
            linked_names[i*k + min(i, m):(i+1)*k + min(i+1, m)]
            for i in range(3)
        ]

        # Finally adding these names as fields to the embed
        for names in chunked_names:
            index_embed.add_field(name="‎", value="\n".join(names))

        await interaction.response.send_message(embed=index_embed, ephemeral=hidden, view=SearchResults(muses))
            



# Mapping for the embed information list.
information_mapping = ["Age", "Rank", "Position", 
                       "Department", "Division", "Platoon",
                       "Status", "Partner", "Sexuality"]


# Creates the embed from the retrived lists
async def get_character_embed(interaction: discord.Interaction, muse_list: list, info_list: list) -> discord.Embed:
    
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

    # Sets the muse thumbnail to the user's avatar, to be changed.
    if info_list[12] is not None: 
        try:
            file = discord.File(info_list[12], filename=info_list[12].split("/")[-1])
            embed.set_thumbnail(url=f"attachment://{info_list[12].split("/")[-1]}")
        except:
            file = None
    else: embed.set_thumbnail(url=interaction.guild.get_member(muse_list[1]).avatar.url); file = None

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


async def setup(bot):
    await bot.add_cog(characterIndex(bot))