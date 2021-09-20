import asyncio
import logging
from typing import List, Tuple, Callable

from twitchio.ext import commands

from kogbeans.apis.stream_elements import StreamElementsGambleAPI

logger = logging.getLogger("kogbeans.cogs.gamble_meta")


class GambleMetaCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        broadcaster_name: str,
        default_user_cooldown: int,
        default_luck: int,
        lucky_dice_luck_increment: int,
        lucky_dice_luck_limit: int,
        lucky_dice_duration: int,
        spam_roulette_duration: int,
        lucky_dice_reward_name: str,
        spam_roulette_reward_name: str,
        stream_elements_account_id: str,
        stream_elements_jwt_token: str,
    ):
        self.bot = bot
        self._broadcaster_name = broadcaster_name
        self._default_user_cooldown = default_user_cooldown
        self._default_luck = default_luck
        self._lucky_dice_luck_increment = lucky_dice_luck_increment
        self._lucky_dice_luck_limit = lucky_dice_luck_limit
        self._lucky_dice_duration = lucky_dice_duration
        self._spam_roulette_duration = spam_roulette_duration
        self._lucky_dice_reward_name = lucky_dice_reward_name
        self._spam_roulette_reward_name = spam_roulette_reward_name
        self._stream_elements_api = StreamElementsGambleAPI(
            stream_elements_account_id, stream_elements_jwt_token
        )

        self._current_luck = default_luck
        self._lucky_dice_semaphore = asyncio.Semaphore(lucky_dice_luck_limit)
        self._lucky_dice_lock = asyncio.Lock()
        self._spam_roulette_lock = asyncio.Lock()

    @commands.Cog.event()
    async def event_ready(self):
        logger.info(f"{self.bot.nick} GambleMetaCog is ready!")

    async def handle_lucky_dice(self):
        async with self._lucky_dice_semaphore:
            channel = self.bot.get_channel(self._broadcaster_name)

            async with self._lucky_dice_lock:
                new_luck = self._current_luck + self._lucky_dice_luck_increment
                await channel.send(f"Lucky Dice from {self._current_luck} to {new_luck} in 3...")
                for message in ["2...", "1..."]:
                    await asyncio.sleep(1)
                    await channel.send(message)

                await asyncio.sleep(1)
                text, status = await self._stream_elements_api.set_luck(new_luck)
                if status != 200:
                    logger.error(f"Error status {status} | {text}")
                    await channel.send("Sorry! Bot broke")
                    return
                else:
                    logger.info(f"Increased luck to {self._current_luck} from {new_luck}")
                    await channel.send("GO!")
                    self._current_luck = new_luck

            await asyncio.sleep(self._lucky_dice_duration)

            async with self._lucky_dice_lock:
                new_luck = self._current_luck - self._lucky_dice_luck_increment
                await channel.send(
                    f"Lucky Dice Ended! Luck from {self._current_luck} to {new_luck}"
                )
                text, status = await self._stream_elements_api.set_luck(new_luck)
                if status != 200:
                    logger.error(f"Error status {status} | {text}")
                    return
                else:
                    logger.info(f"Decreased luck to {self._current_luck} to {new_luck}")
                    self._current_luck = new_luck

    async def handle_spam_roulette(self):
        async with self._spam_roulette_lock:
            channel = self.bot.get_channel(self._broadcaster_name)

            await channel.send("Starting Spam Roulette 3...")
            for message in ["2...", "1..."]:
                await asyncio.sleep(1)
                await channel.send(message)

            await asyncio.sleep(1)
            text, status = await self._stream_elements_api.set_user_cooldown(1)
            if status != 200:
                logger.error(f"Error status {status} | {text}")
                await channel.send("Sorry! Bot broke")
                return
            else:
                logger.info(f"Removed user cooldown")
                await channel.send("GO!")

            await asyncio.sleep(self._spam_roulette_duration)

            await channel.send("Spam Roulette Ended!")
            text, status = await self._stream_elements_api.set_user_cooldown(
                self._default_user_cooldown
            )
            if status != 200:
                logger.error(f"Error status {status} | {text}")
            else:
                logger.info(f"Set user cooldown to {self._default_user_cooldown}")

    def get_reward_redemptions(self) -> List[Tuple[str, Callable]]:
        return [
            (self._spam_roulette_reward_name, self.handle_spam_roulette),
            (self._lucky_dice_reward_name, self.handle_lucky_dice),
        ]


def prepare(bot: commands.Bot, **kwargs):
    cog = GambleMetaCog(bot=bot, **kwargs)
    bot.add_cog(cog)
    return cog
