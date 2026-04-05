import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID", "")

DATABASE_PATH = "dnd_campaign.db"
CAMPAIGN_NAME = "Lost Mines of Phandelver"

# AI model settings
AI_MODEL = "claude-sonnet-4-6"
AI_MAX_TOKENS = 1024

# D&D constants
MAX_PLAYERS = 6
MIN_PLAYERS = 1
