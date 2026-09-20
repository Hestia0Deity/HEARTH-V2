import discord, sqlite3, os, dotenv, random, re
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from cogs.administration import log_action

# Delete these if not necessary
db = sqlite3.connect("main.db")
cursor = db.cursor()

# Main class
class reservations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"""CREATE TABLE IF NOT EXISTS reservationsDatabase(
        guildID INT, 
        userID INT, 
        reservation STRING, 
        expires STRING, 
        messageID INT)""")
        db.commit()
        print("reservations.py -- ONLINE")
        self.reservations_loop.start()




    # /reserve-faceclaim faceclaim:string
    @app_commands.command(name="reserve-faceclaim", description="Reserves a faceclaim")
    async def reserve_faceclaim(self, interaction:discord.Interaction, faceclaim:str):
        # Checks if anyone has used this faceclaim
        cursor.execute(f"SELECT muse, faceclaim FROM museDatabase WHERE guildID = ? AND faceclaim = ?",
                       (interaction.guild.id, faceclaim))
        usedFaceclaim = cursor.fetchone()
        if usedFaceclaim is not None:
            await interaction.response.send_message(f"The muse {usedFaceclaim[0]} is already using the faceclaim {usedFaceclaim[1]}.", ephemeral=True)
            return

        # Checks if anyone has reserved this faccelaim
        cursor.execute(f"SELECT userID, reservation, expires FROM reservationsDatabase WHERE guildID = ? AND reservation  = ?",
                       (interaction.guild.id, faceclaim))
        resFaceclaim = cursor.fetchone()
        if resFaceclaim is not None:
            await interaction.response.send_message(f"<@{resFaceclaim[0]}> has reserved the faceclaim **`{resFaceclaim[1]}`** "+
                                                    f"already. This reservation expires on <t:{resFaceclaim[2]}> (<t:{resFaceclaim[2]}:R>)")
            return

        # Gets the reservations channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'RESERVATIONS'",
                               (interaction.guild.id,))
        reservationChannel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Message ID
        expires = int(datetime.timestamp(datetime.now() + timedelta(days=7)))
        message = await reservationChannel.send(f"{faceclaim} — <@{interaction.user.id}>\n-# <t:{expires}:d> (<t:{expires}:R>)")

        # Adds the faceclaim to the reserved list.
        cursor.execute(f"INSERT INTO reservationsDatabase(guildID, userID, reservation, expires, messageID) VALUES (?, ?, ?, ?, ?)",
                       (interaction.guild.id, interaction.user.id, faceclaim, expires, message.id))
        db.commit()

        # Confirmation message
        await interaction.response.send_message(f"The faceclaim `{faceclaim}` has been successfully reserved.", ephemeral=True)


    # /delete-reservation
    @app_commands.command(name="delete-reservation", description="Deletes a faceclaim reservation")
    async def delete_reservation(self, interaction:discord.Interaction, faceclaim:str):
        # Searches for the reservation
        cursor.execute(f"SELECT userID, reservation, expires, messageID FROM reservationsDatabase WHERE guildID = ? AND reservation  = ?",
                        (interaction.guild.id, faceclaim))
        resFaceclaim = cursor.fetchone()

        # Checks if it exists
        if resFaceclaim is None:
            await interaction.response.send_message(f"Could not find a reservation with the faceclaim: **`{faceclaim}`**.", ephemeral=True)
            return
        # Checks if the user owns it or if they have the manage roles permission
        if resFaceclaim[0] != interaction.user.id and not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(f"You do not own this reservation, and/or you are not a staff member.", ephemeral=True)
            return

        # Deletes the reservation
        cursor.execute(f"DELETE FROM reservationsDatabase WHERE guildID = ? AND reservation = ?",
                       (interaction.guild.id, faceclaim))
        db.commit()

        # Gets the reservations channel
        cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'RESERVATIONS'",
                                        (interaction.guild.id,))
        reservationChannel = interaction.guild.get_channel(cursor.fetchone()[0])

        # Gets the message & deletes it.
        message = await reservationChannel.fetch_message(resFaceclaim[3])
        await message.delete()

        # Logs the action
        await log_action(interaction, 2, "/delete-reservation",
                         f"<@{interaction.user.id}> has deleted the reservation for the faceclaim: **`{faceclaim}`**\n"+
                         f"-# This reservation was owned by <@{resFaceclaim[0]}>")

        # Sends the confirmation message
        await interaction.response.send_message(f"Deleted the reservation for {faceclaim} successfully.", ephemeral=True)


    # /search-faceclaims
    @app_commands.command(name="search-faceclaims", description="Searches to see is a faceclaim is reserved or used.")
    async def search_faceclaims(self, interaction:discord.Interaction, faceclaim:str, hidden:bool = True):
        # Gets all muses with a faceclaim like the search query from the muse database
        cursor.execute("SELECT muse, faceclaim, userID FROM museDatabase WHERE faceclaim LIKE ? AND guildID = ? COLLATE NOCASE",
                       (f'%{faceclaim}%', interaction.guild.id))
        museFaceclaims = cursor.fetchall()
        # Gets all muses with a faceclaim like the search query from the reservation database
        cursor.execute("SELECT reservation, expires, userID FROM reservationsDatabase WHERE reservation LIKE ? AND guildID = ? COLLATE NOCASE",
                               (f'%{faceclaim}%', interaction.guild.id))
        resFaceclaims = cursor.fetchall()

        # If there is none with that faceclaim found
        if len(museFaceclaims) == 0 and len(resFaceclaims) == 0:
            await interaction.response.send_message("Could not find any muses or reservations with that faceclaim.", ephemeral=True)
            return

        embeds = []
        # If there is one or more muses with that faceclaim found
        if len(museFaceclaims) > 0:
            fc_list = ""
            for fc in museFaceclaims:
                fc_list += f" - {fc[1]} : {fc[0]}\n  -# <@{fc[2]}>\n"
            embed = discord.Embed(
                title=f"Active Muses Matching: {faceclaim}",
                colour=discord.Colour.blue(), description=fc_list
            )
            embeds.append(embed)

        # If there is one or more muses with that reservation found
        if len(resFaceclaims) > 0:
            fc_list = ""
            for fc in resFaceclaims:
                fc_list += f" - {fc[0]} : <t:{fc[1]}:d> (<t:{fc[1]}:R>)\n  -# <@{fc[2]}>\n"
            embed = discord.Embed(
                title=f"Reserved Muses Matching: {faceclaim}",
                colour=discord.Colour.orange(), description=fc_list
            )
            embeds.append(embed)

        await interaction.response.send_message("The following were found matching the search query:", embeds=embeds, ephemeral=hidden)


    # loop to check faceclaim reservations
    @tasks.loop(minutes=15)
    async def reservations_loop(self):
        # Creates the timestamps
        now_timestamp = int(datetime.timestamp(datetime.now()))

        # Gets all timestamps going to expire in a day
        cursor.execute(f"SELECT * FROM reservationsDatabase WHERE expires < {now_timestamp}")
        expiring_reservations = cursor.fetchall()

        # Loops through all expiring reservations, sending a warning and updating them.
        for reservation in expiring_reservations:
            # Gets the reservation channel
            cursor.execute("SELECT classID FROM administrationDatabase WHERE guildID = ? AND purpose = 'RESERVATIONS'",
                                            (reservation[0],))
            reservationChannel:discord.TextChannel = self.bot.get_channel(cursor.fetchone()[0])

            # Gets the message & deletes it.
            message = await reservationChannel.fetch_message(reservation[4])
            await message.delete()

            # Deletes it from the database
            cursor.execute("DELETE FROM reservationsDatabase WHERE guildID = ? AND reservation = ?",
                           (reservation[0], reservation[2]))
            db.commit()

        




# Sets the actual cogs up.
async def setup(bot):
    await bot.add_cog(reservations(bot))