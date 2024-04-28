from discord.ext import commands
import os
from dotenv import load_dotenv
import discord
from stats import get_player_stats, get_team_stats 
from shotchart import shot_map
from discord.ui import View, Button

# Load the environment variable
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


class OptionsDropdown(discord.ui.Select):
    def __init__(self):
        options=[
            discord.SelectOption(label='Live NBA Scores', description='Live scores from nba games 🏀'),
            discord.SelectOption(label = 'Play-by-play', description='NBA play-by-play of the game 📢'),
            discord.SelectOption(label='Player Stats', description='Player stats📊'),
            discord.SelectOption(label ='Team Stats', description='Team_stats📊'),
            discord.SelectOption(label ='Shot Chart', description='Shot chart of players and teams 📈'),
            discord.SelectOption(label='Machine Learning Prediction', description='Simple ML-based predictions of a game🤖'),
            discord.SelectOption(label='Latest News', description='Reliable news sources 📰'),
        
        ]
        super().__init__(placeholder='Choose an option', options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Live NBA Scores":
           interaction.response.send_message("Unknown option selected, please try again.")
        elif self.values[0] == "Play-by-play":
           interaction.response.send_message("Unknown option selected, please try again.")
        elif self.values[0] == "Player Stats":
             await interaction.response.send_modal(PlayerStats())
        elif self.values[0] == "Team Stats":
             await interaction.response.send_modal(TeamStats())
        elif self.values[0] == "Shot Chart":
               await interaction.response.send_modal(ShotChart())
        elif self.values[0] == "Machine Learning Prediction":
            interaction.response.send_message("Unknown option selected, please try again.")
        elif self.values[0] == "Latest News":
          interaction.response.send_message("Unknown option selected, please try again.")
        else:
            await interaction.response.send_message("Unknown option selected, please try again.")

# get inputs for the functions
class PlayerStats(discord.ui.Modal, title="Player Stats"):
    # Text input for player name
    player_name = discord.ui.TextInput(label="Enter the NBA player's name:")

    async def on_submit(self, interaction: discord.Interaction):

        player_stats = await get_player_stats(self.player_name.value)
        await interaction.response.send_message(player_stats)
        
class TeamStats(discord.ui.Modal, title="Team Stats"):

    team_name = discord.ui.TextInput(label="Enter an NBA team name:")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loading_message = await interaction.followup.send("Loading team stats...")
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
        buffer, error = await shot_map(self.player_name, chart_type='regular')
        if buffer:
            await interaction.followup.send(file=discord.File(fp=buffer, filename='shot_chart.png'))
        # go back to home or display charts again?
        else:
            await interaction.followup.send("An error occurred: " + error)

    @discord.ui.button(label="Heatmap Shot Chart", style=discord.ButtonStyle.danger)
    async def heatmap_chart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        buffer, error = await shot_map(self.player_name, chart_type='heatmap')
        if buffer:
            await interaction.followup.send(file=discord.File(fp=buffer, filename='heatmap_chart.png'))
        else:
            await interaction.followup.send("An error occurred: " + error)
            
        
class ShotChart(discord.ui.Modal, title="Shot Chart"):
    # Text input for player name
    player_chart_name = discord.ui.TextInput(label="Enter the NBA player's name:")

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = ChartTypeView(self.player_chart_name.value)
        await interaction.followup.send("Select chart type:", view=view)


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
    await ctx.send('Hello, I an NBA bot. Type !nba to get started!')
    


# Event to confirm the bot is online
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
bot.run(TOKEN)
