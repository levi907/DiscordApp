"""
Lost Mines of Phandelver — Discord D&D Bot
Entry point: loads cogs, syncs slash commands, initializes database.
"""
import asyncio
import logging
import sys
import discord
from discord.ext import commands
from config import DISCORD_TOKEN, DEV_GUILD_ID
import data.database as db

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("dnd_bot")

COGS = [
    "cogs.game_cog",
    "cogs.character_cog",
    "cogs.combat_cog",
    "cogs.actions_cog",
]

class DnDBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await db.init_db()
        log.info("Database initialized.")

        # Register persistent views so buttons work after bot restarts
        from utils.views import CombatView, ExplorationView
        self.add_view(CombatView())
        self.add_view(ExplorationView())
        log.info("Persistent views registered.")

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"Loaded cog: {cog}")
            except Exception as e:
                log.error(f"Failed to load cog {cog}: {e}")

        # Sync slash commands
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            # Copy to guild for instant sync, then wipe global to prevent duplicates
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            self.tree.clear_commands(guild=None)
            await self.tree.sync()   # push empty global tree
            log.info(f"Slash commands synced to dev guild {DEV_GUILD_ID} (global commands cleared)")
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally (may take up to 1 hour)")

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="Lost Mines of Phandelver | /help"
            )
        )

    async def on_command_error(self, ctx, error):
        log.error(f"Command error: {error}")

bot = DnDBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN is not set. Copy .env.example to .env and fill in your tokens.")
        sys.exit(1)
    bot.run(DISCORD_TOKEN, log_handler=None)
