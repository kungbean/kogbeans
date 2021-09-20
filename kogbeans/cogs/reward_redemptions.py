import asyncio
import logging
from typing import List, Tuple, Callable

from twitchio.ext import commands
from twitchio.ext import pubsub


logger = logging.getLogger("kogbeans.cogs.reward_redemptions")


class RewardRedemptionsCog(commands.Cog):

    """Handles all Channel Point redemptions from a PubSub subscription

    Attributes:
        bot: TwitchIO bot
        _broadcaster_oauth_token: Broadcaster OAUTH token
        _broadcaster_id: Broadcaster ID
        _rewards: List of (reward name, async reward function)
    """

    def __init__(
        self,
        bot: commands.Bot,
        broadcaster_oauth_token: str,
        broadcaster_id: int,
        rewards: List[Tuple[str, Callable]],
    ):
        self.bot = bot
        self._broadcaster_oauth_token = broadcaster_oauth_token
        self._broadcaster_id = broadcaster_id
        self._rewards = rewards

    @commands.Cog.event()
    async def event_ready(self):
        """When cog is ready, set up bot channel points event listener,
        then set up PubSub subscription to listen to channel point events.
        """

        @self.bot.event()
        async def event_pubsub_channel_points(event: pubsub.PubSubChannelPointsMessage):
            """Loops through all the rewards this function should handle. If it finds an eligible reward,
            then run the await function to do the logic for the reward."""
            logger.info(f"Received {event.reward.title} reward")
            for reward_title, reward_fn in self._rewards:
                if event.reward.title == reward_title:
                    await reward_fn()
                    break

            await asyncio.sleep(0)

        self.bot.pubsub = pubsub.PubSubPool(self.bot)
        topics = [pubsub.channel_points(self._broadcaster_oauth_token)[self._broadcaster_id]]
        await self.bot.pubsub.subscribe_topics(topics)
        logger.info(f"{self.bot.nick} RewardRedemptionsCog is ready!")


def prepare(bot: commands.Bot, **kwargs):
    cog = RewardRedemptionsCog(bot=bot, **kwargs)
    bot.add_cog(cog)
    return cog
