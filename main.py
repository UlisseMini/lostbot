import discord
import dotenv
import os

dotenv.load_dotenv()

TOKEN = os.environ['DISCORD_BOT_TOKEN']
GUILD_ID = os.environ['GUILD_ID']
THREAD_ONLY_CATEGORY_ID = os.environ['THREAD_ONLY_CATEGORY_ID']

bot = discord.Bot(intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    print(f'[{message.author}]: {message.content}')
    if message.content.startswith('.hello'):
        await message.channel.send('Hello!')

    # create a thread if it's a thread only channel!
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.category_id == THREAD_ONLY_CATEGORY_ID:
            name = message.content[:50]
            thread = await message.create_thread(name=name, auto_archive_duration=60)
            await thread.send(f"Thread created (thread only channel)")



@bot.slash_command(guild_ids=[GUILD_ID])
async def hello(ctx):
    await ctx.respond("Hello!")



bot.run(TOKEN)
