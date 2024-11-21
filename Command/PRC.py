import discord
from discord.ext import commands
from bson import ObjectId

from main import db
from APIs.PRC_API import PRC_API

class PRC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

             