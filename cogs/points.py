import discord, sqlite3, os, dotenv, random, re
import sqlite3
from datetime import datetime
from discord.ext import commands
from discord import app_commands


dotenv.load_dotenv()
db = sqlite3.connect("main.db")
cursor = db.cursor()


class points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db.execute(f"CREATE TABLE IF NOT EXISTS pointsDatabase(guildID INT, userID INT, points INT, bumps INT, totalMessages INT)")
        db.commit()
        print("points.py -- ONLINE")




    # Bump & Points system, +10 points for a bump, +1 point every five messages
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.webhook_id: return
        if message.interaction_metadata: return

        if message.author.bot: # If they are a bot
            if (message.author.id == 735147814878969968 # If they're fibo
            and message.content.__contains__("bumping")): # And if fibo is talking about bumping
                # Gets the userID from the message
                userID = re.search(r'<@(\d+)>', message.content)
                if userID is None: return
                else: userID = int(userID.group(1))
                
                # Gets their previous stats
                cursor.execute("SELECT * FROM pointsDatabase WHERE guildID = ? AND userID = ?",
                               (message.guild.id, userID))
                results = cursor.fetchone()
                
                # Updates the point and bump count
                if results is None:
                    cursor.execute("INSERT OR IGNORE INTO pointsDatabase(guildID, userID, points, bumps, totalMessages) VALUES (?,?,?,?,?)",
                               (message.guild.id, userID, 10, 1, 1))
                else:
                    cursor.execute("UPDATE pointsDatabase SET points = ?, bumps = ? WHERE guildID = ? AND userID = ?",
                                   (results[2] + 10, results[3] + 1, message.guild.id, userID))
                db.commit()
        else:
            # Getting their results.
            cursor.execute("SELECT * FROM pointsDatabase WHERE guildID = ? AND userID = ?",
                               (message.guild.id, message.author.id))
            results = cursor.fetchone()

            if results is None:
                # If there isn't any record, add one.
                cursor.execute("INSERT OR IGNORE INTO pointsDatabase(guildID, userID, points, bumps, totalMessages) VALUES (?,?,?,?,?)",
                               (message.guild.id, message.author.id, 0, 0, 1))
                db.commit()
            else:
                # If the results are divisible by 5, adds a point
                if results[4]%5 == 0: updatedPoints = results[2] + 1
                else: updatedPoints = results[2]

                # Updating the database
                cursor.execute("UPDATE pointsDatabase SET totalMessages = ?, points = ? WHERE guildID = ? AND userID = ?",
                                   (results[4]+1, updatedPoints, message.guild.id, message.author.id))
                db.commit()




    # Gets someone's stats
    @app_commands.command(name="get-user-stats", description="Returns an embed with a user's points, bumps, messages and muse count.")
    async def get_user_stats(self, interaction:discord.Interaction, user:discord.Member = None, hidden:bool = True):
        user = user or interaction.user
        cursor.execute("SELECT * FROM pointsDatabase WHERE guildID = ? AND userID = ?",
                               (interaction.guild.id, user.id))
        result = cursor.fetchone()

        # Checks if they have any stats
        if result is None: await interaction.response.send_message("This user has no statistics, they might not have sent any messages yet.", ephemeral=True); return

        # Counts their total characters
        cursor.execute(f"SELECT COUNT(*) FROM museDatabase WHERE guildID = ? AND userID = ?",
                       (interaction.guild.id, user.id))
        totalCount = cursor.fetchone()[0]

        # Puts the stats into an embed
        statEmbed = discord.Embed(
            title=f"{user.display_name}'s Statistics",
            colour=discord.Colour.orange(),
            description=f"This is the total points, muses and bumps for <@{user.id}>"
        )
        statEmbed.set_thumbnail(url=user.display_avatar.url)
        statEmbed.add_field(name="Total Points", value=result[2])
        statEmbed.add_field(name="Total Bumps", value=result[3])
        statEmbed.add_field(name="Total Muses", value=totalCount)

        # Sends the stat embed
        await interaction.response.send_message(embed=statEmbed, ephemeral=hidden)




    @app_commands.command(name="get-leaderboard", description="Gets the leaderboards for points, bumps or muses")
    @app_commands.choices(leaderboard=[
        app_commands.Choice(name="Points Leaderboard", value="points"),
        app_commands.Choice(name="Bump Leaderboard", value="bumps"),
        app_commands.Choice(name="Muse Leaderboard", value="muses")
    ])
    async def get_leaderboard(self, interaction:discord.Interaction, leaderboard:app_commands.Choice[str], hidden:bool=True):
        if leaderboard.value == "muses": # If its top muse count, selects the top five from the museDatabase
            cursor.execute(f"SELECT userID, COUNT(*) FROM museDatabase WHERE guildID = ? GROUP BY userID ORDER BY COUNT(*) DESC LIMIT 5",
                           (interaction.guild.id,))
            result = cursor.fetchall()
        else: # If its not, selects the top five from the pointsDatabase for the specified value
            cursor.execute(f"SELECT userID, {leaderboard.value} FROM pointsDatabase WHERE guildID = ? ORDER BY {leaderboard.value} DESC LIMIT 5",
                           (interaction.guild.id,))
            result = cursor.fetchall()
        
        ## Creates the embed
        leaderboardEmbed = discord.Embed(
            colour=discord.Colour.gold(),
            title=leaderboard.name,
            description=f"The leaderboard for {leaderboard.value} is:\n"
        )

        ## Loops through and adds each to the embed
        count = 0
        for user in result:
            leaderboardEmbed.description += f"\n{count}. <@{user[0]}> : {user[1]}"
            count+=1
        
        ## Sends the finished embed.
        await interaction.response.send_message(embed=leaderboardEmbed, ephemeral=hidden)
            




async def setup(bot):
    await bot.add_cog(points(bot))