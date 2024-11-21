import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import os
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from pkgutil import iter_modules
import logging

from APIs.PRC_API import PRC_API

load_dotenv()

logger = logging.getLogger(__name__)
discord.utils.setup_logging(level=logging.INFO)

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo = None
        self.db = None
        self.erlc_keys = None
        self.prc_api = None

    async def setup_hook(self):
        """Set up the bot's resources."""
        self.mongo = self._init_mongo()
        self.db = self.mongo["robloxhelper"]
        self.erlc_keys = self.db["erlc_keys"]

        self.prc_api = PRC_API(self, os.getenv("API_URL"), os.getenv("API_KEY"))

        self._load_extensions()
        self.change_status.start()

    def _init_mongo(self):
        """Initialize MongoDB connection."""
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
            mongo_client.server_info()
            logger.info("Connected to MongoDB")
            return mongo_client
        except (ConnectionFailure, ServerSelectionTimeoutError):
            logger.critical("===============================\n===============================")
            logger.critical("Failed to connect to MongoDB")
            logger.critical("===============================\n===============================")
            raise

    def _load_extensions(self):
        """Load all command extensions dynamically."""
        commands_path = "Commands"
        commands_to_load = [name for _, name, _ in iter_modules([commands_path], f"{commands_path}.")]
        for command in commands_to_load:
            try:
                self.load_extension(command)
                logger.info(f"Loaded command: {command}")
            except Exception as e:
                logger.error(f"Failed to load command {command}: {e}")

    @tasks.loop(hours=1)
    async def change_status(self):
        """Periodic task to change the bot's status."""
        status = "👀 Coming Soon!"
        logger.info("Changing bot status")
        await self.change_presence(activity=discord.CustomActivity(name=status))

    @change_status.before_loop
    async def before_change_status(self):
        """Ensure the bot is ready before starting the status change loop."""
        await self.wait_until_ready()

    async def on_ready(self):
        """Event handler for when the bot is ready."""
        logger.info(f"Logged in as {self.user} ({self.user.id})")
        print("------")


def main():
    intents = discord.Intents.default()
    intents.presences = False
    intents.message_content = True
    intents.members = True
    intents.messages = True
    bot = Bot(
        command_prefix=commands.when_mentioned_or(">"),
        intents=intents,
    )

    try:
        bot.run(os.getenv("DISCORD_TOKEN"))
    except Exception as e:
        logger.critical(f"Bot encountered a fatal error: {e}")


if __name__ == "__main__":
    main()
