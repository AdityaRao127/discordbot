from nba_api.stats.endpoints import playbyplayv3, scoreboardv2
from nba_api.live.nba.endpoints import scoreboard
from datetime import datetime, timedelta
from dateutil import parser, tz
import pytz 
from nba_api.live.nba.endpoints import boxscore
from nba_api.live.nba.endpoints import playbyplay
from nba_api.stats.static import players
import asyncio 

async def get_play_by_play(game_id, last_action_number=-1):
    try:
        print(f"Getting play-by-play data for game {game_id}...")
        loop = asyncio.get_running_loop()
        pbp = await loop.run_in_executor(None, playbyplay.PlayByPlay, game_id)
        actions = await loop.run_in_executor(None, pbp.get_dict)
        actions = actions['game']['actions']

        # reverse order of actions, having most recent action at the top
        actions = sorted(actions, key=lambda x: x['actionNumber'], reverse=True)

        new_actions = [action for action in actions if action['actionNumber'] > last_action_number]
        print([action['actionNumber'] for action in new_actions], last_action_number)
        
        if new_actions:
            latest_action = new_actions[0]
            player = players.find_player_by_id(latest_action['personId'])
            if player is not None:
                play_by_play_dict = {
                    'player': player['full_name'],
                    'actionNumber': latest_action['actionNumber'],
                    'period': latest_action['period'],
                    'clock': latest_action['clock'],
                    'actionType': latest_action['actionType'],
                    'description': latest_action['description']
                }
            else:
                play_by_play_dict = {
                    'player': '',
                    'actionNumber': latest_action['actionNumber'],
                    'period': latest_action['period'],
                    'clock': latest_action['clock'],
                    'actionType': latest_action['actionType'],
                    'description': latest_action['description']
                }
            last_action_number = latest_action['actionNumber']
            return [play_by_play_dict], last_action_number
        else:
            return [], last_action_number
    except Exception as e:
        print(f"Error retrieving play-by-play data: {e}")
        return [], last_action_number

    
async def fetch_ongoing_game_ids():
    try:
        board = scoreboard.ScoreBoard()
        games = board.games.get_dict()
        ongoing_games = []
        now = datetime.now(tz=pytz.utc)

        for game in games:
            game_time_utc = parser.parse(game["gameTimeUTC"]).replace(tzinfo=pytz.utc)
            game_end_time_utc = game_time_utc + timedelta(hours=3)

            if game['gameStatus'] == 2 and now >= game_time_utc and now <= game_end_time_utc:
                ongoing_games.append({
                    "gameId": game["gameId"],
                    "matchup": f"{game['awayTeam']['teamName']} vs {game['homeTeam']['teamName']}",
                    "time": game_time_utc.astimezone(pytz.timezone('America/Los_Angeles')).strftime('%I:%M %p %Z')
                })

        return ongoing_games
    except Exception as e:
        return f"Error fetching ongoing games: {str(e)}"

async def fetch_live_games():
    try:
        board = scoreboard.ScoreBoard()
        games = board.games.get_dict()
        upcoming_games = []
        ongoing_games = []
        finished_games = []
        
        # Current time in Pacific timezone
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(tz=pytz.utc)
        now_pacific = now.astimezone(pacific_tz)
        today_date = now_pacific.date()

        for game in games:
            # Game time in Pacific timezone
            game_time_utc = parser.parse(game["gameTimeUTC"]).replace(tzinfo=pytz.utc)
            game_time_pst = game_time_utc.astimezone(pacific_tz)
            game_date = game_time_pst.date()

            home_team = game['homeTeam']['teamName']
            away_team = game['awayTeam']['teamName']
            home_score = game['homeTeam']['score']
            away_score = game['awayTeam']['score']
            game_status = game['gameStatus']
            game_id = game['gameId']

            time_display = game_time_pst.strftime('%I:%M %p %Z')

            if game_date < today_date:  # Game is from yesterday or earlier
                continue  # Skip previous days
            elif game_date == today_date:  # Game is today
                if game_status == 1:  # Game is upcoming
                    upcoming_games.append(f"**{away_team} vs. {home_team}** starts at {time_display}")
                elif game_status == 2:  # Game is ongoing
                    pbp = playbyplay.PlayByPlay(game_id)
                    actions = pbp.get_dict()['game']['actions']
                    current_period = actions[-1]['period']
                    current_clock = actions[-1]['clock']
                    clock_parts = current_clock.split('T')[1].split('M')
                    minutes = int(clock_parts[0])
                    seconds = clock_parts[1].split('S')[0]
                    formatted_clock = f"{minutes}:{seconds}"
                    ongoing_games.append(f"**{away_team} vs. {home_team}**\n`Q{current_period}` `{formatted_clock}`\nCurrent score: {away_team} `{away_score}` - `{home_score}` {home_team}\n")
                elif game_status == 3:  # Game is completed
                    if home_score > away_score:
                        winner = f"{home_team} win"
                    else:
                        winner = f"{away_team} win"
                    finished_games.append(f"{away_team} vs. {home_team}\nScore: ||`{away_score} - {home_score}`, ***{winner}***||\n")
            else:  # Game is from tomorrow or later
                pass  # implement later

        # Date formatting
        formatted_date = f"{today_date.strftime('%B')} {ordinal(today_date.day)}"
        summary = f"NBA Games on **{formatted_date}** ({today_date.month}/{today_date.day})\n""\n"

        if ongoing_games or finished_games or upcoming_games:
            # append to results
            if upcoming_games:
                summary += "⏰ Upcoming games ⏰\n" + "\n".join(upcoming_games) + "\n"
            if ongoing_games:
                summary += "🏀 Ongoing games 🏀\n" + "\n".join(ongoing_games) + "\n"
            if finished_games:
                summary += "✅ Completed games ✅\n" + "\n".join(finished_games) + "\n"
        else:
            summary += "\nNo games today.\n"
        
        return summary

    except Exception as e:
        return f"Error fetching live games: {str(e)}"

def ordinal(n): #  get date suffix
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix