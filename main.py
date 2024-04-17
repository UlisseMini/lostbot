import discord
import dotenv
import random
from datetime import datetime, timedelta
import os
import asyncio
import json
from pairing import PairingAlgorithm

dotenv.load_dotenv()

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GUILD_ID = os.environ["GUILD_ID"]
THREAD_ONLY_CATEGORY_ID = int(os.environ["THREAD_ONLY_CATEGORY_ID"])

bot = discord.Bot(intents=discord.Intents.all())


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
            name = message.content[:50]
            thread = await message.create_thread(name=name, auto_archive_duration=60)
            await thread.send(f"Thread created (thread only channel)")


@bot.slash_command(guild_ids=[GUILD_ID])
async def hello(ctx):
    await ctx.respond("Hello!")


@bot.slash_command(guild_ids=[GUILD_ID])
async def add_1_on_1(ctx: discord.Interaction):
    # add 1on1 role to user
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    await ctx.author.add_roles(role)
    await ctx.respond("You have signed up for 1on1s!")


@bot.slash_command(guild_ids=[GUILD_ID])
async def remove_1_on_1(ctx):
    # remove 1on1 role from user
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    await ctx.author.remove_roles(role)
    await ctx.respond("You have removed yourself from 1on1s!")


@bot.slash_command(guild_ids=[GUILD_ID])
async def show_1on1_signed_up(ctx):
    # show all users with 1on1 role
    role = discord.utils.get(ctx.guild.roles, name="1on1")
    users = [member.name for member in ctx.guild.members if role in member.roles]
    await ctx.respond(f"Users with 1on1 role: {', '.join(users)}")


async def pair_for_1on1s(guild):
    role = discord.utils.get(guild.roles, name="1on1")
    users = [member.id for member in guild.members if role in member.roles]
    algorithm = PairingAlgorithm(users)
    # get the last message from "1on1-history" and load it into history
    channel = discord.utils.get(guild.channels, name="1on1-history")
    last_message = channel.last_message
    if last_message:
        algorithm.load_history(last_message.content)
    else:
        algorithm.load_history("{}")
    # find all the users with role 1on1filler and pick a random one
    filler_role = discord.utils.get(guild.roles, name="1on1filler")
    filler_id = [member.id for member in guild.members if filler_role in member.roles]
    random.shuffle(filler_id)
    filler_id = filler_id[0] if filler_id else None
    pairs = algorithm.pair_people(filler=filler_id)
    h = algorithm.serialize_history()
    # save the serialized history into a message to load later
    channel = discord.utils.get(guild.channels, name="1on1-history")
    await channel.send(h)
    # save the pairs into "1on1-pairs"
    channel = discord.utils.get(guild.channels, name="1on1-pairs")
    await channel.send(json.dumps(pairs))
    return pairs

def mention_(user, safe=False):
    mention = user.mention
    if safe:
        # just return @ and then the user's nick
        return f"@{user.display_name}"
    else:
        return user.mention


async def display_pairs(guild, pairs, user_asked=None, ctx=None, channel=None):
    if ctx and channel:
        raise ValueError("Only one of 'ctx' and 'channel' should be provided, not both.")
    if not ctx and not channel:
        raise ValueError("Either 'ctx' or 'channel' must be provided.")
    # for each pair, get the user from their discriminator and mention them
    users = []
    for pair in pairs:
        user1 = discord.utils.get(guild.members, id=pair[0])
        user2 = discord.utils.get(guild.members, id=pair[1])
        if user_asked:
            # basically, we don't want to mention users if only a single user asked what the pairs were
            if user_asked == pair[0]:
                users.append(f"{mention_(user1)} — {mention_(user2, safe=True)}")
            elif user_asked == pair[1]:
                users.append(f"{mention_(user1, safe=True)} — {mention_(user2)}")
            else:
                users.append(f"{mention_(user1, safe=True)} — {mention_(user2, safe=True)}")
        else:
            users.append(f"{mention_(user1)} — {mention_(user2)}")

    if ctx:
        await ctx.respond(f"1on1 pairs: {', '.join(users)}")
    elif channel:
        await channel.send(f"1on1 pairs: {', '.join(users)}")


@bot.slash_command(guild_ids=[GUILD_ID])
async def pair_1on1s(ctx):
    # require admin
    if not ctx.author.guild_permissions.administrator:
        await ctx.respond("You must be an admin to run this command.")
        return
    pairs = await pair_for_1on1s(ctx.guild)
    await display_pairs(ctx.guild, pairs, ctx=ctx)


@bot.slash_command(guild_ids=[GUILD_ID])
async def show_1on1_pairs(ctx):
    channel = discord.utils.get(ctx.guild.channels, name="1on1-pairs")
    last_message = channel.last_message
    if last_message:
        pairs_json = last_message.content
        pairs = json.loads(pairs_json)
        await display_pairs(ctx.guild, pairs, user_asked=ctx.author.id, ctx=ctx)
    else:
        await ctx.respond("No pairs found")


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


async def weekly_task():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        while not bot.is_closed():
            next_run = next_friday()
            await asyncio.sleep((next_run - datetime.now()).total_seconds())
            # get the last message in 1-1s and then get a context from that
            pairs = await pair_for_1on1s(guild)
            # get the 1-1s channel
            channel = discord.utils.get(guild.channels, name="1-1s")
            await display_pairs(guild, pairs, channel=channel)



bot.loop.create_task(weekly_task())
bot.run(TOKEN)
