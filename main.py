import discord
import dotenv
import random
from datetime import datetime, timedelta
import os
import asyncio
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Tuple, List, Dict, Optional
from pairing import History
from util import add_save_load

dotenv.load_dotenv()

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ["GUILD_ID"]
THREAD_ONLY_CATEGORY_ID = int(os.environ["THREAD_ONLY_CATEGORY_ID"])

bot = discord.Bot(intents=discord.Intents.all())

# only ping the user if they asked
def mention_(guild, uid: int, asked=None, always_ping = False):
    user = discord.utils.get(guild.members, id=uid)
    if always_ping or user.id == asked:
        return user.mention
    else:
        return f"@{user.display_name}"

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    print(f"[{message.author}]: {message.content}")
    if message.content.startswith(".hello"):
        await message.channel.send("Hello!")

    # create a thread if it's a thread only channel!
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.category_id == THREAD_ONLY_CATEGORY_ID:
            # discord UI glitch when you create a thread too fast, this is a mitigation.
            await asyncio.sleep(1)
            # or in case of image-only message
            name = message.content[:50] or "New Thread"
            thread = await message.create_thread(name=name, auto_archive_duration=60)
            await thread.send(f"Thread created (thread only channel)")


@bot.slash_command(guild_ids=[GUILD_ID])
async def hello(ctx):
    await ctx.respond("Hello!")

# the one on one stuff

@add_save_load("pairings.json", "1on1-pairs")
@dataclass_json
@dataclass
class WeeklyPairings:
    # people who are unpaired
    # 2 ways to be on this list:
    # there are an odd number
    # even number but you already had 1-on-1 with other people/person
    unpaired: List[int] = field(default_factory=list)
    # people who are paired this week
    paired: List[Tuple[int, int]] = field(default_factory=list)


# the `1on1` role is to be autopaired every week
@bot.slash_command(guild_ids=[GUILD_ID])
async def add_1_on_1(ctx: discord.Interaction):
    # add 1on1 role to user
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    await ctx.author.add_roles(role)
    await ctx.respond("You have signed up for 1on1s!")
@bot.slash_command(guild_ids=[GUILD_ID])
async def remove_1_on_1(ctx):
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    await ctx.author.remove_roles(role)
    await ctx.respond("You have removed yourself from 1on1s!")

@bot.slash_command(guild_ids=[GUILD_ID])
async def open_to_extra_1_on_1(ctx: discord.Interaction):
    # add 1on1filler role to user
    role = discord.utils.get(ctx.guild.roles, name="1on1filler")
    await ctx.author.add_roles(role)
    await ctx.respond("You have signed up to be available for more 1on1s (for example when there are an odd number)!")
@bot.slash_command(guild_ids=[GUILD_ID])
async def remove_extra_1_on_1(ctx: discord.Interaction):
    role = discord.utils.get(ctx.guild.roles, name="1on1filler")
    await ctx.author.remove_roles(role)
    await ctx.respond("You have removed yourself from being available for extra 1on1s!")


@bot.slash_command(guild_ids=[GUILD_ID])
async def show_1on1_signed_up(ctx: discord.Interaction):
    # show all users with 1on1 role
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    users = [member.display_name for member in ctx.guild.members if role in member.roles]
    await ctx.respond(f"Users who will get pinged weekly to remind to sign up for 1-on-1s {', '.join(users)}")



async def display_pairs(guild, pairings: WeeklyPairings, user_asked: int = None, always_ping=False, ctx=None, channel: discord.TextChannel = None):
    if not (bool(ctx) ^ bool(channel)):
        raise ValueError("Ctx xor channel must be provided")
    # for each pair, get the user from their discriminator and mention them
    s = ""
    if len(pairings.paired) > 0:
        s += "*1on1 pairs:*\n"
        for pair in pairings.paired:
            s += f"{mention_(guild, pair[0], asked=user_asked, always_ping=always_ping)} — {mention_(guild, pair[1], asked=user_asked, always_ping=always_ping)}\n"
    elif len(pairings.unpaired) > 0:
        s += "*waiting to be paired:*\n"
        for user_id in pairings.unpaired:
            s += f"{mention_(guild, user_id, asked=user_asked, always_ping=always_ping)}\n"
    else:
        s += "No pairings made yet"

    if ctx:
        await ctx.respond(s)
    elif channel:
        await channel.send(s)
    else:
        assert False # we need ctx or channel



@bot.slash_command(guild_ids=[GUILD_ID])
async def show_1on1_pairs(ctx: discord.Interaction):
    wps = await WeeklyPairings.load(ctx.guild)
    if wps:
        await display_pairs(ctx.guild, wps, user_asked=ctx.author.id, ctx=ctx)
    else:
        await ctx.respond("No pairs found")

async def pair_weekly_users(guild: discord.Guild):
    hist = await History.load_or_create_new(guild)
    wps = await WeeklyPairings.load(guild)
    if wps:
        # also include people who were waiting to be paired last time
        unpaired = set(wps.unpaired)
    else:
        unpaired = set()
    opt_in = list(set([member.id for member in guild.members if discord.utils.get(member.roles, name="1on1")]) + unpaired)
    pairs, unpaired = hist.pair_people(opt_in=opt_in)
    wps = WeeklyPairings(unpaired=unpaired, paired=pairs)
    c1 = wps.save(guild)
    c2 = hist.save(guild)
    await asyncio.gather(c1, c2)
    return wps

@bot.slash_command(guild_ids=[GUILD_ID])
async def pairme(ctx: discord.Interaction):
    hist = await History.load_or_create_new(ctx.guild)
    pairs = await WeeklyPairings.load(ctx.guild)
    person = ctx.author.id
    if any(person in pair for pair in pairs.paired):
        # TODO should we allow anyone to just sink all the pairs?
        await ctx.respond("You are already paired this week!")
        return
    unused = [pairs.unpaired, [member.id for member in ctx.guild.members if discord.utils.get(member.roles, name="1on1filler")]]
    other = hist.pair_person(person, unused)
    if other == None:
        await ctx.respond("No one to pair with, sorry :(")
        return
    await hist.save(ctx.guild)
    pairs.paired.append((person, other))
    await pairs.save(ctx.guild)
    await ctx.respond(f"Paired {mention_(ctx.guild, person, always_ping=True)} with {mention_(ctx.guild, other, always_ping=True)}")

@bot.slash_command(guild_ids=[GUILD_ID])
async def pair_1on1s(ctx: discord.Interaction):
    if not ctx.author.guild_permissions.administrator:
        await ctx.respond("You must be an admin to run this command.")
        return
    wps = await pair_weekly_users(ctx.guild)
    await display_pairs(ctx.guild, wps, ctx=ctx, always_ping=True)


def next_friday():
    now = datetime.now()
    # 4 represents Friday, calculating days until the next Friday
    days_until_friday = (4 - now.weekday()) % 7
    if days_until_friday == 0 and now.hour >= 9:  # If today is Friday and it's past 9 AM
        days_until_friday = 7  # Wait until next Friday
    next_friday = now + timedelta(days=days_until_friday)
    r = next_friday.replace(hour=7, minute=0, second=0, microsecond=0)  # Set time to 7:00 AM
    print(f"running pairs in {r}")
    return r

def one_on_one_chan(guild: discord.Guild):
    return discord.utils.get(guild.channels, name="1-1s")

# a dict mapping guilds to the message we are listening for reacts on each one
current_messages: Dict[discord.Guild, int] = {}

async def weekly_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        while not bot.is_closed():
            next_run = next_friday()
            await asyncio.sleep((next_run - datetime.now()).total_seconds())
            # get the 1-1s channel
            wps = pair_weekly_users(guild)
            chan = one_on_one_chan(guild)
            await display_pairs(guild, wps, always_ping=True, channel=chan)


bot.loop.create_task(weekly_task())
bot.run(TOKEN)
