import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import requests

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
    """Fetch the printer status and job details from OctoPrint."""
    headers = {"X-Api-Key": OCTOPRINT_API_KEY}
    try:
        # Get printer status
        response = requests.get(f"{OCTOPRINT_URL}/api/printer", headers=headers)
        response.raise_for_status()
        printer_data = response.json()

        state = printer_data['state']['text']  # Printer state, e.g., 'Operational', 'Printing'
        temps = printer_data.get('temperature', {})
        bed_temp = temps.get('bed', {}).get('actual', "N/A")
        tool_temp_actual = temps.get('tool0', {}).get('actual', "N/A")
        tool_temp_target = temps.get('tool0', {}).get('target', "N/A")

        # Get job details
        job_response = requests.get(f"{OCTOPRINT_URL}/api/job", headers=headers)
        job_response.raise_for_status()
        job_data = job_response.json()

        part_name = job_data['current']['file']['name'] if 'current' in job_data else "No current print job"
        print_time = job_data['current']['time'] if 'current' in job_data else 0
        estimated_print_time = job_data['current']['estimatedPrintTime'] if 'current' in job_data else 0

        return {
            "state": state,
            "part_name": part_name,
            "print_time": print_time,
            "estimated_print_time": estimated_print_time,
            "bed_temp": bed_temp,
            "tool_temp_actual": tool_temp_actual,
            "tool_temp_target": tool_temp_target
        }
    except requests.RequestException as e:
        print(e)
        return None

@bot.tree.command(name="admin_printerstatus", description="Get the current printer status, print time, part name, and webcam feed (Admin only)")
async def admin_printerstatus(interaction: discord.Interaction):
    # Check if the user has the admin role
    user_roles = interaction.user.roles
    has_admin_role = any(role.name == ADMIN_ROLE_NAME for role in user_roles)

    await interaction.response.defer()  # Defer response while fetching data

    printer_status = await fetch_printer_status()

    if printer_status is None:
        await interaction.followup.send("Failed to fetch printer status. Please check OctoPrint connection.")
        return

    # Create an embed to present both the printer status and the webcam feed
    embed = discord.Embed(title="Admin Printer Status and Live Webcam Feed", color=discord.Color.dark_green())
    embed.add_field(name="Printer Status", value=printer_status['state'], inline=False)
    embed.add_field(name="Part Name", value=printer_status['part_name'], inline=False)
    embed.add_field(name="Print Time", value=f"{printer_status['print_time'] // 60} minutes", inline=True)  # Convert seconds to minutes
    embed.add_field(name="Estimated Print Time", value=f"{printer_status['estimated_print_time'] // 60} minutes", inline=True)  # Convert seconds to minutes
    embed.add_field(name="Bed Temperature", value=f"{printer_status['bed_temp']}°C", inline=True)
    embed.add_field(name="Tool Temperature", value=f"{printer_status['tool_temp_actual']}°C / {printer_status['tool_temp_target']}°C", inline=True)
    embed.add_field(name="Live Webcam Feed", value=f"[Click here to view the live feed]({OCTOPRINT_WEBCAM_URL})", inline=False)

    # Send the response
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="printerstatus", description="Get the current printer status and print time (Available for everyone)")
async def printerstatus(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer response while fetching data

    printer_status = await fetch_printer_status()

    if printer_status is None:
        await interaction.followup.send("Failed to fetch printer status. Please check OctoPrint connection.")
        return

    # Create an embed to present the printer status
    embed = discord.Embed(title="Printer Status", color=discord.Color.blue())
    embed.add_field(name="Printer Status", value=printer_status['state'], inline=False)
    embed.add_field(name="Part Name", value=printer_status['part_name'], inline=False)
    embed.add_field(name="Print Time", value=f"{printer_status['print_time'] // 60} minutes", inline=True)  # Convert seconds to minutes
    embed.add_field(name="Estimated Print Time", value=f"{printer_status['estimated_print_time'] // 60} minutes", inline=True)  # Convert seconds to minutes
    embed.add_field(name="Bed Temperature", value=f"{printer_status['bed_temp']}°C", inline=True)
    embed.add_field(name="Tool Temperature", value=f"{printer_status['tool_temp_actual']}°C / {printer_status['tool_temp_target']}°C", inline=True)

    # Send the response
    await interaction.followup.send(embed=embed)

# Run the bot
bot.run(DISCORD_TOKEN)