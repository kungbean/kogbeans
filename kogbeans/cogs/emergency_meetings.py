import asyncio
import logging
import json
from typing import List, Tuple, Callable

import aiohttp
from twitchio.ext import commands


logger = logging.getLogger("kogbeans.cogs.emergency_meeting")


class EmergencyMeetingCog(commands.Cog):

    """Starts an Among Us styled Emergency Meeting where chat can _eject_ someone.
    Winner will get timeout from chat.

    Attributes:
        bot: TwitchIO bot
        _meeting_duration: Emergency Meetings in seconds
        _timeout_duration: Winner timeout duration in seconds
        _broadcaster_name: Username of streamer
        _reward_name: Name of reward on Twitch
        _eject_ties: Ejects all 1st place ties if true
        _current_mods: Set of all current mods
        _current_users: Set of all current users
        _voter_to_candidate: Dictionary of voter to candidate
        _candidate_to_count: Dictionary of candidate to vote count
    """

    def __init__(
        self,
        bot: commands.Bot,
        meeting_duration: int,
        timeout_duration: int,
        broadcaster_name: str,
        reward_name: str,
        eject_ties: bool,
    ):
        self.bot = bot
        self._meeting_duration = meeting_duration
        self._timeout_duration = timeout_duration
        self._broadcaster_name = broadcaster_name
        self._reward_name = reward_name
        self._eject_ties = eject_ties
        self._current_mods = set()
        self._current_users = set()
        self._meeting_lock = asyncio.Lock()
        self._vote_lock = asyncio.Lock()
        self._voter_to_candidate = {}
        self._candidate_to_count = {}

    @commands.Cog.event()
    async def event_ready(self):
        logger.info(f"{self.bot.nick} EmergencyMeetingCog is ready!")

    async def _handle_reward_redemption(self):
        """Function to start an emergency meeting.
        This function is passed to the RewardRedemptionsCog so the pubsub event listener
        can run this to start emergency meetings.

        This function does things in this order:
        - Clears existing votes and counts
        - Uses Twitch API to get current mods / users in chat
        - Waits for waits to come in
        - Gets top candidates
        - Announces winners
        """
        channel = self.bot.get_channel(self._broadcaster_name)

        async with self._meeting_lock:
            await self._clear_votes()
            await self._update_users()
            await channel.send(
                f"Who is the impostor? Use !vote in the next {self._meeting_duration} seconds!"
            )
            await asyncio.sleep(self._meeting_duration)

        top_candidates = await self._top_candidates()
        await self._announce_winners(channel, top_candidates)

    def get_reward_redemptions(self) -> List[Tuple[str, Callable]]:
        return [(self._reward_name, self._handle_reward_redemption)]

    @commands.command()
    async def vote(self, ctx):
        logger.debug(f"{ctx.author.name} - {ctx.message.content}")
        if self._meeting_lock.locked():
            voter = ctx.author.name
            parts = ctx.message.content.split()
            if len(parts) == 2:
                candidate = parts[1].strip().strip("@")
                await self._vote_for(ctx, voter, candidate)
            else:
                await ctx.send(f"{ctx.author.name}, please vote like - !vote @username")
        else:
            await ctx.send(f"{ctx.author.name}, there is no Emergency Meeting.")

    async def _vote_for(self, ctx, voter: str, candidate: str):
        async with self._vote_lock:
            voter_key = voter.lower()
            candidate_key = candidate.lower()
            if candidate_key == self._broadcaster_name.lower():
                await ctx.send(f"{ctx.author.name} thinks they can eject streamer LUL")
                return
            elif candidate_key in self._current_mods:
                await ctx.send(f"{ctx.author.name}, mods cannot be ejected... for now")
                return
            elif (
                candidate_key not in self._current_users
                and candidate_key not in self._voter_to_candidate
            ):
                await ctx.send(f"{ctx.author.name}, that user doesn't seem to be here.")
                return

            if voter_key in self._voter_to_candidate:
                old_candidate_key = self._voter_to_candidate[voter_key]
                self._candidate_to_count[old_candidate_key] -= 1

            self._voter_to_candidate[voter_key] = candidate_key
            self._candidate_to_count[candidate_key] = (
                self._candidate_to_count.get(candidate_key, 0) + 1
            )
            await ctx.send(
                f"{ctx.author.name} voted for {candidate}, with {self._candidate_to_count[candidate_key]} votes!"
            )

    async def _clear_votes(self):
        async with self._vote_lock:
            self._voter_to_candidate = {}
            self._candidate_to_count = {}

    async def _top_candidates(self) -> List[Tuple[str, int]]:
        async with self._vote_lock:
            ranking = sorted(
                list(self._candidate_to_count.items()), key=lambda x: x[1], reverse=True
            )
            top_candidates = []
            max_votes = 0
            for candidate, votes in ranking:
                if not top_candidates:
                    max_votes = votes
                    top_candidates.append((candidate, votes))
                else:
                    if max_votes == votes:
                        top_candidates.append((candidate, votes))
                    else:
                        break

            return top_candidates

    async def _announce_winners(self, channel, top_candidates: List[Tuple[str, int]]):
        if not top_candidates:
            await channel.send(f"No one voted, no one was ejected.")
        elif len(top_candidates) > 1 and not self._eject_ties:
            candidates = ", ".join(top_candidates.keys())
            await channel.send(f"There was a tie between {candidates}. No one was ejected.")
        else:
            for candidate, votes in top_candidates:
                await channel.send(
                    f"/timeout {candidate} {self._timeout_duration} You were ejected by crewmates!"
                )
                await channel.send(f"{candidate} was ejected with {votes} votes!")

    async def _update_users(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://tmi.twitch.tv/group/user/{self._broadcaster_name}/chatters"
            ) as response:
                text = await response.text()

        data = json.loads(text)
        chatters = data["chatters"]
        self._current_mods = {u.lower() for u in chatters["moderators"]}
        self._current_users = {u.lower() for u in chatters["vips"] + chatters["viewers"]}


def prepare(bot: commands.Bot, **kwargs):
    cog = EmergencyMeetingCog(bot=bot, **kwargs)
    bot.add_cog(cog)
    return cog
