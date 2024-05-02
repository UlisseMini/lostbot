import discord
import io
def load_class_from_channel(cls, channame):
    async def f(guild):
        # get the channel
        channel = discord.utils.get(guild.channels, name=channame)
        messages = await channel.history(limit=1).flatten()
        try:
            if messages:
                last_message = messages[0]
                pairs_json = await last_message.attachments[0].read()
                wps = cls.from_json(pairs_json)
            else:
                return None
        except Exception as e:
            return None
        return wps
    return f
def save_class_to_channel(cls, filename, channame):
    async def f(self, guild):
        channel = discord.utils.get(guild.channels, name=channame)
        await channel.send(file=discord.File(fp=io.StringIO(self.to_json()), filename=filename))
    return f
def add_save_load(filename, channame):
    def decorator(cls):
        cls.load = load_class_from_channel(cls, channame)
        cls.save = save_class_to_channel(cls, filename, channame)
        return cls

    return decorator