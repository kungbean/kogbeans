import os
import logging

from twitchio.ext import commands

from kogbeans.cogs import reward_redemptions
from kogbeans.cogs import emergency_meetings
from kogbeans.cogs import gamble_meta


logger = logging.getLogger("kogbeans")


class MyBot(commands.Bot):
    async def event_ready(self):
        logger.info(f"{self.nick} is ready!")

    async def event_command_error(self, context, error):
        """Suppress CommandNotFound errors"""
        if isinstance(error, commands.errors.CommandNotFound):
            return
        else:
            super().event_command_error(context, error)


def main():

    logger.setLevel("DEBUG")
    formatter = formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel("DEBUG")
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    bot = MyBot(
        token=os.environ["BOT_IRC_TOKEN"],
        prefix="!",
        initial_channels=[os.environ["BROADCASTER_CHANNEL"]],
    )

    emergency_meetings_cog = emergency_meetings.prepare(
        bot=bot,
        meeting_duration=60,
        timeout_duration=20,
        broadcaster_name=os.environ["BROADCASTER_CHANNEL"],
        reward_name="Emergency Meeting!",
        eject_ties=True,
    )
    gamble_meta_cog = gamble_meta.prepare(
        bot=bot,
        broadcaster_name=os.environ["BROADCASTER_CHANNEL"],
        default_user_cooldown=120,
        default_luck=45,
        lucky_dice_luck_increment=10,
        lucky_dice_luck_limit=5,
        lucky_dice_duration=600,
        spam_roulette_duration=60,
        lucky_dice_reward_name="Lucky Dice",
        spam_roulette_reward_name="Spam Roulette",
        stream_elements_account_id=os.environ["STREAMELEMENTS_CHANNEL_ID"],
        stream_elements_jwt_token=os.environ["STREAMELEMENTS_JWT_TOKEN"],
    )

    rewards = (
        emergency_meetings_cog.get_reward_redemptions() + gamble_meta_cog.get_reward_redemptions()
    )
    reward_redemptions.prepare(
        bot=bot,
        broadcaster_oauth_token=os.environ["BROADCASTER_USER_OAUTH_TOKEN"],
        broadcaster_id=int(os.environ["BROADCASTER_CHANNEL_ID"]),
        rewards=rewards,
    )

    bot.run()


if __name__ == "__main__":
    main()
