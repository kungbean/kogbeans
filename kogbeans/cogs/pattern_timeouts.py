import re
import logging
from dataclasses import dataclass
from typing import List, Dict

import twitchio
from twitchio.ext import commands


logger = logging.getLogger("kogbeans.cogs.pattern_timeouts")


@dataclass
class PatternTimeout:

    """A single rule for pattern timeouts

    Attributes:
        pattern: Regex string to match
        users: List of users to apply rule to, or an empty list for everyone
        timeout: Timeout in seconds
        reason: Timeout reason to show user
    """

    pattern: str
    users: List[str]
    timeout: int
    reason: str = ""

    @property
    def regex(self):
        if not hasattr(self, "_regex"):
            self._regex = re.compile(self.pattern, re.IGNORECASE)
        return self._regex

    @property
    def user_set(self):
        if not hasattr(self, "_user_set"):
            self._user_set = set(u.lower() for u in self.users)
        return self._user_set


class PatternTimeoutsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, patterns: List[PatternTimeout]):
        self.bot = bot
        self._patterns = sorted(patterns, key=lambda x: x.timeout, reverse=True)

    @commands.Cog.event()
    async def event_ready(self):
        logger.info(f"{self.bot.nick} PatternTimeoutsCog is ready!")

    @commands.Cog.event()
    async def event_message(self, message: twitchio.Message):
        if message.echo:
            return

        for pattern in self._patterns:
            if message.author:
                if message.author.name.lower() in pattern.user_set or not pattern.user_set:
                    if pattern.regex.search(message.content.lower()):
                        context = await self.bot.get_context(message)
                        timeout_command = f"/timeout {message.author.name} {pattern.timeout} {pattern.reason}".strip()
                        logger.info(f"{timeout_command} | {message.content}")
                        await context.send(timeout_command)
                        return


def prepare(bot: commands.Bot, patterns: List[Dict]):
    patterns = [PatternTimeout(**kwargs) for kwargs in patterns]
    cog = PatternTimeoutsCog(bot, patterns)
    bot.add_cog(cog)
    return cog
