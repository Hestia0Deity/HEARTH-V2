import discord, sqlite3, os, dotenv, random, re
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from cogs.administration import log_action

# Delete these if not necessary
db = sqlite3.connect("main.db")
cursor = db.cursor()

# Main class
class relations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"""CREATE TABLE IF NOT EXISTS relationsDatabase(
                   guildID INT,
                   userID INT,
                   muse STRING,
                   relationMuse STRING,
                   relationType STRING,
                   blurb STRING,
                   PRIMARY KEY (guildID, userID, muse, relationMuse)
                   FOREIGN KEY (guildID, userID, muse) REFERENCES museDatabase (guildID, userID, muse)
                   ON DELETE CASCADE ON UPDATE CASCADE
                   FOREIGN KEY (relationMuse) REFERENCES museDatabase(muse)
                   ON DELETE CASCADE ON UPDATE CASCADE)""")
        db.commit()
        print("relations.py -- ONLINE")




    # Relations autocomplete
    async def relation_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        options = ["Enemies", "Rivals", "Acquaintances", "Friends", "Close Friends", "Familial", "Dating", "Married"]
        return [app_commands.Choice(name=option, value=option) for option in options if option.lower().startswith(current.lower())][:25]


    # Adds a relationship between muses
    @app_commands.command(name="add-relation", description="Adds a relationship between two muses, requires ownership of one of the two muses.")
    @app_commands.describe(
        muse_1 = "The muse you own for this relationship.",
        muse_2 = "The other muse in this relationship",
        relation = "The type of relationship"
    )
    @app_commands.autocomplete(relation = relation_autocomplete)
    async def add_relationship(self, interaction:discord.Interaction, muse_1: str, muse_2: str, relation:str):
        # Checks to make sure that both characters actually exist
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_1, interaction.guild.id))
        muse_1_info = cursor.fetchone()
        if muse_1_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_1, ephemeral=True)
            return
        
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_2, interaction.guild.id))
        muse_2_info = cursor.fetchone()
        if muse_2_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_2, ephemeral=True)
            return

        # Checks to make sure that the user owns the first muse
        if interaction.user.id not in muse_1_info:
            await interaction.response.send_message("You do not own muse 1.", ephemeral=True)
            return

        # Checks if it already exists
        cursor.execute("SELECT * FROM relationsDatabase WHERE guildID = ? AND muse = ? AND relationMuse = ?",
                       (interaction.guild.id, muse_1, muse_2))
        check = cursor.fetchone()
        if check is not None:
            await interaction.response.send_message("A relationship between these two muses already exists.", ephemeral=True)
            return

        await interaction.response.send_modal(EditRelation((muse_1, muse_2), relation, "", False))




    # Edits a relation between muses
    @app_commands.command(name="edit-relation", description="Edits an existing relationship between two muses, requires ownership of one of the two muses.")
    @app_commands.describe(
        muse_1 = "The muse you own for this relationship.",
        muse_2 = "The other muse in this relationship",
        relation = "The type of updated relationship"
    )
    @app_commands.autocomplete(relation = relation_autocomplete)
    async def edit_relationship(self, interaction:discord.Interaction, muse_1: str, muse_2: str, relation:str):
        # Checks to make sure that both characters actually exist
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_1, interaction.guild.id))
        muse_1_info = cursor.fetchone()
        if muse_1_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_1, ephemeral=True)
            return
        
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_2, interaction.guild.id))
        muse_2_info = cursor.fetchone()
        if muse_2_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_2, ephemeral=True)
            return

        # Checks to make sure that the user owns the first muse
        if interaction.user.id not in muse_1_info:
            await interaction.response.send_message("You do not own muse 1.", ephemeral=True)
            return

        # Checks if it already exists
        cursor.execute("SELECT muse, relationMuse, blurb FROM relationsDatabase WHERE guildID = ? AND muse = ? AND relationMuse = ?",
                        (interaction.guild.id, muse_1, muse_2))
        muses = cursor.fetchone()
        if muses is None:
            await interaction.response.send_message("There is no relationship beetween these two muses.", ephemeral=True)
            return

        await interaction.response.send_modal(EditRelation((muses[0], muses[1]), relation, muses[2], True))




    # Views all the relations for a muse
    @app_commands.command(name="list-relations", description="Lists all the relations for a specified muse")
    @app_commands.describe(
        muse = "The name of the muse you want to search",
        hidden = "Whether only you can see the list."
    )
    async def list_relations(self, interaction:discord.Interaction, muse:str, hidden:bool = True):
        # Checks if the muse even exists
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse, interaction.guild.id))
        muse_1_info = cursor.fetchone()
        if muse_1_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse, ephemeral=True)
            return

        # Gets all the relations for that muse
        cursor.execute("SELECT * FROM relationsDatabase WHERE muse = ? AND guildID = ?",
                       (muse, interaction.guild.id))
        outgoing_relations = cursor.fetchall()
        cursor.execute("SELECT * FROM relationsDatabase WHERE relationMuse = ? AND guildID = ?",
                               (muse, interaction.guild.id))
        incoming_relations = cursor.fetchall()

        # Checks if they have any relations
        if len(outgoing_relations) == 0 and len(incoming_relations) == 0: 
            await interaction.response.send_message("This muse has no relations.", ephemeral=True)
            return

        embeds = []

        # Embed for all incoming relationships
        if len(outgoing_relations) != 0:
            ir_embed = discord.Embed(
                title=f"Relationships from {muse} → Others",
                colour=discord.Colour.blue(),
                description=f"Relations from {muse}'s perspective."
            )
            for relation_type, relations in divide_relations(outgoing_relations, True).items():
                ir_embed.add_field(name=relation_type, value='\n'.join(relations))
            embeds.append(ir_embed)

        # Embed for all outgoing relationships
        if len(incoming_relations) != 0:
                    or_embed = discord.Embed(
                        title=f"Relationships from Others → {muse}",
                        colour=discord.Colour.orange(),
                        description=f"Relations with {muse} as the subject, may be duplicates of the above."
                    )
                    for relation_type, relations in divide_relations(incoming_relations, False).items():
                        or_embed.add_field(name=relation_type, value='\n'.join(relations))
                    embeds.append(or_embed)


        # Sends the list with one (or two) embeds.
        await interaction.response.send_message(embeds=embeds, ephemeral=hidden)




    # Deletes a relation entry
    @app_commands.command(name="delete-relation", description="Deletes the specified relation between muses, provided you own the first muse.")
    @app_commands.describe(
        muse_1 = "The muse you own in this relation",
        muse_2 = "The other muse in this relation"
    )
    async def delete_relation(self, interaction:discord.Interaction, muse_1: str, muse_2:str):
        # Checks to make sure that both characters actually exist
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_1, interaction.guild.id))
        muse_1_info = cursor.fetchone()
        if muse_1_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_1, ephemeral=True)
            return
        
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_2, interaction.guild.id))
        muse_2_info = cursor.fetchone()
        if muse_2_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_2, ephemeral=True)
            return

        # Checks to make sure that the user owns the first muse
        if interaction.user.id not in muse_1_info:
            await interaction.response.send_message("You do not own muse 1.", ephemeral=True)
            return

        # Deletes the relation from the database
        cursor.execute("DELETE FROM relationsDatabase WHERE guildID = ? AND muse = ? AND relationMuse = ?",
                       (interaction.guild.id, muse_1, muse_2))
        db.commit()

        # Logs the deletion
        await log_action(interaction, 1,
                         "/delete-relation",
                         f"<@{interaction.user.id}> has deleted the relation between {muse_1} and {muse_2}")
        
        # Sends the confirmation message
        await interaction.response.send_message(f"Successfully deleted the relation between {muse_1} and {muse_2}\n"+
                                                f"-# Please note this deletes *your* relation entry from {muse_1}, not both if there is another from the other's perspective.", 
                                                ephemeral=True)

        
         




    @app_commands.command(name="search-relation", description="Searches for a relationship between the two muses")
    @app_commands.describe(
        muse_1 = "The first muse in the relationship",
        muse_2 = "The second muse in the relationship.",
        hidden = "Whether only you can see the message or not."
    )
    async def search_relation(self, interaction:discord.Interaction, muse_1: str, muse_2: str, hidden: bool = True):
        # Checks to make sure that both characters actually exist
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_1, interaction.guild.id))
        muse_1_info = cursor.fetchone()
        if muse_1_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_1, ephemeral=True)
            return
        
        cursor.execute("SELECT * FROM museDatabase WHERE muse = ? AND guildID = ?", (muse_2, interaction.guild.id))
        muse_2_info = cursor.fetchone()
        if muse_2_info is None:
            await interaction.response.send_message("Could not find a muse with the name: " + muse_2, ephemeral=True)
            return

        # Gets the relationship for those muses
        cursor.execute("SELECT * FROM relationsDatabase WHERE guildID = ? AND (muse = ? AND relationMuse = ?) " +
                       "OR (muse = ? AND relationMuse = ?)",
                       (interaction.guild.id, muse_1, muse_2, muse_2, muse_1))
        relationship = cursor.fetchall()

        # If there is no relations between either muse
        if len(relationship) == 0:
            await interaction.response.send_message("There is no relation between these muses.", ephemeral=True)
            return
        # If there is only one relation
        elif len(relationship) == 1:
            embed = discord.Embed(title=f"{relationship[0][2]}'s Relation to {relationship[0][3]}",
                                  colour=discord.Colour.orange(),
                                  description=f"**Relation Type:** {relationship[0][4]}\n{relationship[0][5]}")
            await interaction.response.send_message(embed=embed, ephemeral=hidden)
        # If there is relations for both
        elif len(relationship) == 2:
            embed1 = discord.Embed(title=f"{relationship[0][2]}'s Relation to {relationship[0][3]}",
                                  colour=discord.Colour.orange(),
                                  description=f"**Relation Type:** {relationship[0][4]}\n{relationship[0][5]}")
            embed2 = discord.Embed(title=f"{relationship[1][2]}'s Relation to {relationship[1][3]}",
                                  colour=discord.Colour.orange(),
                                  description=f"**Relation Type:** {relationship[1][4]}\n{relationship[1][5]}")
            await interaction.response.send_message(embeds=[embed1, embed2], ephemeral=hidden)
        # how is there more than two????
        else:
            await interaction.response.send_message("Something has gone wrong and this request cannot be fulfilled.", ephemeral=True)
            return




# Modal to create and/or edit a relation.
class EditRelation(discord.ui.Modal):
    blurb = discord.ui.TextInput(label="Relation Blurb", style=discord.TextStyle.long, required=True)

    def __init__(self, muses, relation, old_blurb, exists: bool):
        super().__init__(title=f"{relation} - {muses[0]} & {muses[1]}", timeout=None)
        self.muses = muses
        self.relation = relation
        self.exists = exists
        self.blurb.default = old_blurb

    async def on_submit(self, interaction:discord.Interaction):
        # Adds the updated relation to the database, or edits it if it exists 

        if self.exists == False:
            # Adds into the database
            cursor.execute("INSERT INTO relationsDatabase(guildID, userID, muse, relationMuse, relationType, blurb) VALUES (?, ?, ?, ?, ?, ?)",
                           (interaction.guild.id, interaction.user.id, self.muses[0], self.muses[1], self.relation, self.blurb.value))
            db.commit()

            # Logs the addition
            await log_action(interaction, 0,
                             "/add-relationship",
                             f"<@{interaction.user.id}> has added the relation ({self.relation}) between {self.muses[0]} and {self.muses[1]}")

            # Confirms with the user its been added
            await interaction.response.send_message(f"The relation between {self.muses[0]} and {self.muses[1]} has been added.", ephemeral=True)
        else:
            # Adds into the database
            cursor.execute("UPDATE relationsDatabase SET relationType = ?, blurb = ? WHERE guildID = ? AND muse = ? AND relationMuse = ?",
                          (self.relation, self.blurb.value, interaction.guild.id, self.muses[0], self.muses[1]))
            db.commit()

            # Logs the edit
            await log_action(interaction, 0,
                                         "/edit-relationship",
                                         f"<@{interaction.user.id}> has edited the relation ({self.relation}) between {self.muses[0]} and {self.muses[1]}")

            # Confirms with the user its been edited
            await interaction.response.send_message(f"The relation ({self.relation}) between {self.muses[0]} and {self.muses[1]} has been successfully edited.", ephemeral=True)
    



def divide_relations(relations: list, outgoing = bool):
    divided_relations = {}

    for relation in relations:
        if outgoing == False:
            divided_relations.setdefault(relation[4],[]).append(f"{relation[2]}")
        else:
            divided_relations.setdefault(relation[4],[]).append(f"{relation[3]}")

        
    return divided_relations
    
# def relations_string(relations_dict: dict):
#     total_string = ""
#     string_list = []

#     for type, relations in relations_dict.items():
#         relation_string = f"## {type}\n"
#         for relation in relations:
#             relation_string += f"- {relation}\n"

#         if ((len(total_string) + len(relation_string) + 2) > 2000):
#             string_list.append(total_string)
#             total_string = relation_string
#         else:
#             total_string += relation_string + "\n"

#     string_list.append(total_string)
#     return string_list



    
# Sets the actual cogs up.
async def setup(bot):
    await bot.add_cog(relations(bot))