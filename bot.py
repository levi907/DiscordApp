"""
Lost Mines of Phandelver — Discord D&D Bot
Main entry point.
"""
import asyncio
import logging
import discord
from discord.ext import commands
import data.database as db
from config import DISCORD_TOKEN, DEV_GUILD_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dnd_bot")


class DnDBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Init database
        await db.init_db()
        logger.info("Database initialized.")

        # Load cogs
        cogs = [
            "cogs.game_cog",
            "cogs.character_cog",
            "cogs.combat_cog",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)

        # Sync slash commands
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Slash commands synced to dev guild {DEV_GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally (may take up to 1 hour).")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Game(name="Lost Mines of Phandelver | /help")
        )

    async def on_application_command_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        logger.error(f"Command error: {error}", exc_info=True)
        msg = "An unexpected error occurred. Please try again."
        if interaction.response.is_done():
            await interaction.followup.send(content=f"❌ {msg}", ephemeral=True)
        else:
            await interaction.response.send_message(content=f"❌ {msg}", ephemeral=True)


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set. Copy .env.example to .env and fill in your token.")
        return

    bot = DnDBot()
    bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
