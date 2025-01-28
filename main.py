import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import asyncio

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OCTOPRINT_URL = os.getenv("OCTOPRINT_URL")
OCTOPRINT_API_KEY = os.getenv("OCTOPRINT_API_KEY")
GUILD_ID = os.getenv("GUILD_ID")  
OCTOPRINT_WEBCAM_URL = os.getenv("OCTOPRINT_WEBCAM_URL") 

# Set up bot with the necessary intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Define the role names
ADMIN_ROLE_NAME = "Admin"  # Change this to your admin role name

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    guild = discord.utils.get(bot.guilds, id=int(GUILD_ID))
    try:
        synced = await bot.tree.sync()  # Sync commands with Discord
        print(f"Synced {len(synced)} commands.")
        print(f"Connected to server: {guild.name} guild_id: {guild.id}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        print(f"Bot is not connected to the {guild.name} server with server_id: {guild.id}.")

async def fetch_printer_status():
    """Fetch the printer status, job details, and additional information from OctoPrint."""
    headers = {"X-Api-Key": OCTOPRINT_API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            # Get printer status
            async with session.get(f"{OCTOPRINT_URL}/api/printer", headers=headers, timeout=5) as response:
                response.raise_for_status()
                printer_data = await response.json()

            state = printer_data['state']['text']  # Printer state, e.g., 'Operational', 'Printing'
            temps = printer_data.get('temperature', {})
            bed_temp = temps.get('bed', {}).get('actual', "N/A")
            tool_temp_actual = temps.get('tool0', {}).get('actual', "N/A")
            tool_temp_target = temps.get('tool0', {}).get('target', "N/A")

            # Get job details
            async with session.get(f"{OCTOPRINT_URL}/api/job", headers=headers, timeout=5) as job_response:
                job_response.raise_for_status()
                job_data = await job_response.json()

            part_name = job_data['job']['file']['name'] if 'job' in job_data else "No current print job"
            print_time = job_data['progress']['printTime'] if 'progress' in job_data else 0
            estimated_print_time = job_data['job']['estimatedPrintTime'] if 'job' in job_data else 0
            completion_percentage = round(job_data['progress']['completion'], 1) if 'progress' in job_data else 0
            remaining_print_time = job_data['progress']['printTimeLeft'] if 'progress' in job_data else "N/A"

            return {
                "state": state,
                "part_name": part_name,
                "print_time": print_time,
                "estimated_print_time": estimated_print_time,
                "bed_temp": bed_temp,
                "tool_temp_actual": tool_temp_actual,
                "tool_temp_target": tool_temp_target,
                "completion_percentage": completion_percentage,
                "remaining_print_time": remaining_print_time
            }
        except aiohttp.ClientError as e:
            print(f"Failed to fetch printer status: {e}")
            return None


@bot.tree.command(name="printerstatus", description="Get the current printer status and print time (Available for everyone)")
async def printerstatus(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer response while fetching data

    printer_status = await fetch_printer_status()

    if printer_status is None:
        await interaction.followup.send("Failed to fetch printer status. Please check OctoPrint connection.")
        return
    
     # Safely handle None values for estimated_print_time
    estimated_print_time = printer_status['estimated_print_time']
    estimated_print_time_display = f"{estimated_print_time // 60} minutes" if estimated_print_time else "N/A"


    # Create an embed to present the printer status
     # Create an embed to present the printer status
    embed = discord.Embed(title="Printer Status", color=discord.Color.orange())
    embed.add_field(name="Printer Status", value=printer_status['state'], inline=False)
    embed.add_field(name="Part Name", value=printer_status['part_name'], inline=False)
    embed.add_field(name="Print Time", value=f"{printer_status['print_time'] // 60} minutes", inline=True)
    embed.add_field(name="Estimated Print Time", value=estimated_print_time_display, inline=True)
    embed.add_field(name="Completion", value=f"{printer_status['completion_percentage']}%", inline=True)
    embed.add_field(name="Remaining Print Time", value=f"{printer_status['remaining_print_time'] // 60} minutes", inline=True)
    embed.add_field(name="Bed Temperature", value=f"{printer_status['bed_temp']}°C", inline=True)
    embed.add_field(name="Tool Temperature", value=f"{printer_status['tool_temp_actual']}°C / {printer_status['tool_temp_target']}°C", inline=True)


    # Send the response
    await interaction.followup.send(embed=embed)

# Run the bot
bot.run(DISCORD_TOKEN)
