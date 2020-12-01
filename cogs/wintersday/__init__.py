"""
The IdleRPG Discord Bot
Copyright (C) 2018-2020 Diniboy and Gelbpunkt

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import datetime

import discord

from discord.ext import commands

from cogs.shard_communication import next_day_cooldown
from utils import random
from utils.checks import has_char
from utils.i18n import _, locale_doc

rewards = {
    1: {"crates": 0, "puzzle": False, "money": 500},
    2: {"crates": 0, "puzzle": True, "money": 0},
    3: {"crates": 0, "puzzle": False, "money": 700},
    4: {"crates": 1, "puzzle": False, "money": 0},
    5: {"crates": 0, "puzzle": False, "money": 750},
    6: {"crates": 0, "puzzle": True, "money": 0},
    7: {"crates": 1, "puzzle": False, "money": 0},
    8: {"crates": 0, "puzzle": False, "money": 850},
    9: {"crates": 0, "puzzle": False, "money": 999},
    10: {"crates": 1, "puzzle": False, "money": 0},
    11: {"crates": 0, "puzzle": False, "money": 1000},
    12: {"crates": 0, "puzzle": False, "money": 1100},
    13: {"crates": 0, "puzzle": True, "money": 0},
    14: {"crates": 1, "puzzle": False, "money": 0},
    15: {"crates": 0, "puzzle": False, "money": 1250},
    16: {"crates": 0, "puzzle": False, "money": 1350},
    17: {"crates": 0, "puzzle": True, "money": 0},
    18: {"crates": 0, "puzzle": False, "money": 1499},
    19: {"crates": 1, "puzzle": False, "money": 0},
    20: {"crates": 0, "puzzle": True, "money": 0},
    21: {"crates": 1, "puzzle": False, "money": 0},
    22: {"crates": 0, "puzzle": False, "money": 1500},
    23: {"crates": 0, "puzzle": True, "money": 0},
    24: {"crates": 1, "puzzle": False, "money": 2000},
}


class Christmas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @locale_doc
    async def calendar(self, ctx):
        _("""Look at your Winter Calendar""")
        today = datetime.datetime.now().day
        if today > 25 or today < 1:
            return await ctx.send(_("No calendar to show!"))
        await ctx.send(
            file=discord.File(
                f"assets/calendar/24 days of IdleRPG - {today - 1} open.jpg"
            )
        )

    @has_char()
    @next_day_cooldown()  # truly make sure they use it once a day
    @calendar.command(name="open")
    @locale_doc
    async def _open(self, ctx):
        _("""Open the Winter Calendar once every day.""")
        today = datetime.datetime.utcnow().date()
        christmas_too_late = datetime.date(2020, 12, 25)
        first_dec = datetime.date(2020, 12, 1)
        if today >= christmas_too_late or today < first_dec:
            return await ctx.send(_("It's not calendar time yet..."))
        reward = rewards[today.day]
        reward_text = _("**You opened day {today}!**").format(today=today.day)
        async with self.bot.pool.acquire() as conn:
            if reward["puzzle"]:
                await conn.execute(
                    'UPDATE profile SET "puzzles"="puzzles"+1 WHERE "user"=$1;',
                    ctx.author.id,
                )
                await self.bot.cache.update_profile_cols_rel(ctx.author.id, puzzles=1)
                text = _("A mysterious puzzle piece")
                reward_text = f"{reward_text}\n- {text}"
            if reward["crates"]:
                rarity = random.choice(
                    ["legendary"]
                    + ["magic"] * 2
                    + ["rare"] * 5
                    + ["uncommon"] * 5
                    + ["common"] * 5
                )
                await conn.execute(
                    f'UPDATE profile SET "crates_{rarity}"="crates_{rarity}"+$1 WHERE'
                    ' "user"=$2;',
                    reward["crates"],
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="crates",
                    data={"Rarity": rarity, "Amount": reward["crates"]},
                    conn=conn,
                )
                await self.bot.cache.update_profile_cols_rel(
                    ctx.author.id, **{f"crates_{rarity}": reward["crates"]}
                )
                text = _("{crates} {rarity} crate").format(
                    crates=reward["crates"], rarity=rarity
                )
                reward_text = f"{reward_text}\n- {text}"
            if reward["money"]:
                await conn.execute(
                    'UPDATE profile SET "money"="money"+$1 WHERE "user"=$2;',
                    reward["money"],
                    ctx.author.id,
                )
                await self.bot.log_transaction(
                    ctx,
                    from_=1,
                    to=ctx.author.id,
                    subject="money",
                    data={"Amount": reward["money"]},
                    conn=conn,
                )
                await self.bot.cache.update_profile_cols_rel(
                    ctx.author.id, money=reward["money"]
                )
                reward_text = f"{reward_text}\n- ${reward['money']}"
            if today.day == 24:
                bg_num = random.randint(1, 4)
                bgs = await conn.fetchval(
                    'UPDATE profile SET "backgrounds"=array_append("backgrounds", $1)'
                    ' WHERE "user"=$2 RETURNING "backgrounds";',
                    f"https://idlerpg.xyz/image/winter2020_{bg_num}.png",
                    ctx.author.id,
                )
                await self.bot.cache.update_profile_cols_abs(
                    ctx.author.id, backgrounds=bgs
                )
                text = _(
                    "A special surprise - check out `{prefix}eventbackground` for a new"
                    " Wintersday background!"
                ).format(prefix=ctx.prefix)
                reward_text = f"{reward_text}\n- {text}"
        await ctx.send(reward_text)

    @has_char()
    @commands.command()
    @locale_doc
    async def combine(self, ctx):
        _("""Combine the mysterious puzzle pieces.""")
        if ctx.character_data["puzzles"] != 6:
            return await ctx.send(
                _(
                    "The mysterious puzzles don't fit together... Maybe some are"
                    " missing?"
                )
            )
        bg = random.choice(
            [
                "https://i.imgur.com/iLJEGOf.png",
                "https://i.imgur.com/LDax1ag.png",
                "https://i.imgur.com/FpWXBev.png",
            ]
        )
        async with self.bot.pool.acquire() as conn:
            bgs = await conn.fetchval(
                "UPDATE profile SET backgrounds=array_append(backgrounds, $1) WHERE"
                ' "user"=$2 RETURNING "backgrounds";',
                bg,
                ctx.author.id,
            )
            await conn.execute(
                'UPDATE profile SET "puzzles"=0 WHERE "user"=$1;', ctx.author.id
            )
        await self.bot.cache.update_profile_cols_abs(
            ctx.author.id, backgrounds=bgs, puzzles=0
        )
        await ctx.send(
            _(
                "You combined the puzzles! In your head a voice whispers: *Well done."
                " Now use `{prefix}eventbackground 1` to set your new background that"
                " you just acquired...*"
            ).format(prefix=ctx.prefix)
        )


def setup(bot):
    bot.add_cog(Christmas(bot))
