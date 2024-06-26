from discord.ext import commands
import os
from dotenv import load_dotenv
import discord
from stats import get_player_stats, get_team_stats 
from shotchart import shot_map
from discord.ui import View, Button
from playbyplay import get_play_by_play, fetch_live_games, fetch_ongoing_game_ids
from news import fetch_feed
from discord.ext import commands 
import schedule 
import time
import feedparser
import re
import os
from keep_alive import keep_alive
from datetime import datetime
import asyncio
import tempfile


# Load the environment variable
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL = os.getenv('DISCORD_CHANNEL')
WOJ_FEED = os.getenv('DISCORD_WOJ_TWEETS')
SHAMS_FEED = os.getenv('DISCORD_SHAMS_TWEETS')

FEED_URLS = ['WOJ_FEED', 'SHAMS_FEED']
# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all(), hearbeat_timeout=60)

keep_alive()

class OptionsDropdown(discord.ui.Select):
    def __init__(self):
        options=[
            discord.SelectOption(label='Live NBA Scores', description='Live scores from nba games 🏀'),
            discord.SelectOption(label = 'Play-by-play', description='NBA play-by-play of the game 📢'),
            discord.SelectOption(label='Player Stats', description='Player stats📊'),
            discord.SelectOption(label ='Team Stats', description='Team_stats📊'),
            discord.SelectOption(label='Injury Report', description='Latest injury report of teams 🚑'),
            discord.SelectOption(label ='Shot Chart', description='Shot chart of players 2023-24 season 📈'),
            discord.SelectOption(label='Machine Learning Prediction', description='Simple ML-based predictions of a game🤖'),
            discord.SelectOption(label='Latest News', description='Reliable news sources 📰'),
        
        ]
        super().__init__(placeholder='Choose an option', options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Live NBA Scores":
            live_scores_text = await fetch_live_games()
            await interaction.response.send_message(live_scores_text)
        
        elif self.values[0] == "Play-by-play":
            ongoing_games = await fetch_ongoing_game_ids()
            if ongoing_games:
                view = LiveGamesView(ongoing_games)
                await interaction.response.send_message("Select a game to view play-by-play details:", view=view)
            else:
                await interaction.response.send_message("No live games available at the moment.")
        elif self.values[0] == "Player Stats":
             modal = PlayerStats(timeout=180.0)  
             await interaction.response.send_modal(modal)
        elif self.values[0] == "Team Stats":
             await interaction.response.send_modal(TeamStats())
        elif self.values[0] == "Injury Report":
            await interaction.response.send_message("This feature is coming soon! Try Player/Team Stats, Live Scores, Shot-Chart, or Latest News instead.")
        elif self.values[0] == "Shot Chart":
               await interaction.response.send_modal(ShotChart())
        elif self.values[0] == "Machine Learning Prediction":
            await interaction.response.send_message("This feature is coming soon! Try Player/Team Stats, Live Scores, Shot-Chart, or Latest News instead.")
        elif self.values[0] == "Latest News":
            await interaction.response.send_message("Fetching latest news...")
            feed_urls = [WOJ_FEED, SHAMS_FEED]  # will add more authors soon
            updates = fetch_feed(feed_urls)

            if updates:
                woj_updates = updates[0]
                shams_updates = updates[1]

                woj_message = "Woj's Latest Updates:\n"
                for update in woj_updates[:3]:  # 3 woj latest tweets
                    woj_message += f"**Tweet Content**:\n{update['content']}\n\nAuthor: {update['author']}\nDate and time: {update['published']}\n\n"

                shams_message = "Shams' Latest Updates:\n"
                for update in shams_updates[:3]:  # 3 shams latest tweets
                    shams_message += f"**Tweet Content**:\n{update['content']}\n\nAuthor: {update['author']}\nDate and time: {update['published']}\n\n"

                await interaction.followup.send(woj_message)
                await interaction.followup.send(shams_message)

            else:
                await interaction.response.send_message("Unknown option selected, please try again.")


#auto check every 10 min
#async def run_bot():
 #   await bot.start(TOKEN)
   # schedule.every(10).minutes.do(check_feed)
   # while True:
    #    schedule.run_pending()
      #  await asyncio.sleep(1) 


#auto post tweets from accounts
async def check_feed():
    feed_urls = [WOJ_FEED, SHAMS_FEED]
    updates = fetch_feed(feed_urls)
    for feed_updates in updates:
        for update in feed_updates:  # Post all updates from each feed
            message = f"**Tweet Content**:\n{update['content']}\n\nAuthor: {update['author']}\nDate and time: {update['published']}"
            print("Found tweet")
            channel = bot.get_channel(CHANNEL)
            await channel.send(message)
    else:
        channel = bot.get_channel(CHANNEL)
        await channel.send("No new updates found.")
# manual news tweets 
@bot.command()
async def latest_news(ctx):
    feed_urls = ['WOJ_FEED', 'SHAMS_FEED'] 
    updates = fetch_feed(feed_urls)
    for feed_updates in updates:
        for update in feed_updates[:3]:  # latest 3 updates
            message = f"Author: {update['author']}\nTweet content:\n{update['content']}"
            await ctx.send(message)
    else:
        await ctx.send("No new updates found.")
        
class PlayerStats(discord.ui.Modal, title="Player Stats"):
    player_name = discord.ui.TextInput(label="Enter the NBA player's name:", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        # Acknowledge the interaction
        await interaction.response.defer()
        loading_player_message = await interaction.followup.send(f"Loading {self.player_name.value.title()} stats...")
        player_stats_embed = await get_player_stats(self.player_name.value)
        await loading_player_message.edit(content=None, embed=player_stats_embed)
        
class TeamStats(discord.ui.Modal, title="Team Stats"):

    team_name = discord.ui.TextInput(label="Enter an NBA team name:", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loading_message = await interaction.followup.send(f"Loading {self.team_name.value.title()} stats...")
        team_stats = await get_team_stats(self.team_name.value)
        await loading_message.edit(content=team_stats)
        
# new view for shotcharts
class ChartTypeView(discord.ui.View):
    def __init__(self, player_name):
        super().__init__()
        self.player_name = player_name

    @discord.ui.button(label="Regular Shot Chart", style=discord.ButtonStyle.primary)
    async def regular_chart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        file_path, error = await shot_map(self.player_name, chart_type='regular')
        if file_path:
            await interaction.followup.send(file=discord.File(fp=file_path, filename='shot_chart.png'))
            os.remove(file_path)
        else:
            await interaction.followup.send(f"An error occurred: {error}")

    @discord.ui.button(label="Heatmap Shot Chart", style=discord.ButtonStyle.danger)
    async def heatmap_chart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        file_path, error = await shot_map(self.player_name, chart_type='heatmap')
        if file_path:
            await interaction.followup.send(file=discord.File(fp=file_path, filename='heatmap_chart.png'))
            os.remove(file_path)
        else:
            await interaction.followup.send(f"An error occurred: {error}")

class ShotChart(discord.ui.Modal, title="Shot Chart"):
    player_chart_name = discord.ui.TextInput(label="Enter the NBA player's name:")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = ChartTypeView(self.player_chart_name.value)
        await interaction.followup.send("Select chart type:", view=view)

class LiveGamesView(discord.ui.View):
    def __init__(self, ongoing_games):
        super().__init__()
        self.last_action_numbers = {}
        for game in ongoing_games:
            button = discord.ui.Button(label=f"{game['matchup']} @ {game['time']}",
                                       style=discord.ButtonStyle.primary,
                                       custom_id=f"game_{game['gameId']}")
            button.callback = self.handle_button_click
            self.add_item(button)
            self.last_action_numbers[game['gameId']] = -1

    async def handle_button_click(self, interaction: discord.Interaction):
        game_id = interaction.data['custom_id'].split('_')[1]
        last_action_number = self.last_action_numbers.get(game_id, -1)  # Initialize with -1
        await interaction.response.defer(ephemeral=True)

        start_time = datetime.now()
        game_ended = False

        while True:
            try:
                plays, last_action_number = await get_play_by_play(game_id, last_action_number)
                if plays:
                    for play in reversed(plays):  # Iterate over plays in reverse order
                        formatted_play = f"`{play['actionNumber']}` **{play['period']}:{play['clock']}** ({play['actionType']} {play['description']})"
                        await interaction.followup.send(formatted_play)
                    self.last_action_numbers[game_id] = last_action_number
                elif not plays:
                    # Check if 25 minutes have passed since the last play
                    if (datetime.now() - start_time).total_seconds() / 60 > 25:
                        await interaction.followup.send("No new plays in the last 25 minutes. Ending play-by-play.")
                        break
                else:
                    # Check if the game has ended
                    live_games = await fetch_live_games()
                    for game in live_games:
                        if game['gameId'] == game_id and game['gameStatus'] == 3:
                            if game['homeTeam']['score'] > game['awayTeam']['score']:
                                winner = f"{game['homeTeam']['teamName']} win"
                            else:
                                winner = f"{game['awayTeam']['teamName']} win"
                            await interaction.followup.send(f"Game ended! Final score: {game['awayTeam']['score']} - {game['homeTeam']['score']}, ***{winner}***")
                            game_ended = True
                            break

                    if game_ended:
                        break

                    await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Error during interaction: {e}")
                await interaction.followup.send(f"Error: {str(e)}")
                break
                
class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(OptionsDropdown())

@bot.command()
async def dropdown(ctx):
    """Sends a message with a dropdown."""
    await ctx.send('Please select an option:', view=DropdownView())

@bot.command()
async def nba(ctx):
    """Sends a message with a dropdown."""
    await ctx.send('Please select an option:', view=DropdownView())

@bot.command()
async def hi(ctx):
    """Greet users and provide instructions."""
    await ctx.send('Hello, I am an NBA bot. Type !dropdown to get started!')




@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    

bot.run(TOKEN)

