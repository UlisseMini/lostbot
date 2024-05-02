import discord
import io
class AddSaveLoad:
    @classmethod
    async def load(cls, guild):
        channame = getattr(cls, 'channame')
        channel = discord.utils.get(guild.channels, name=channame)
        messages = await channel.history(limit=1).flatten()
        try:
            if messages:
                last_message = messages[0]
                pairs_json = await last_message.attachments[0].read()
                wps = getattr(cls, 'from_json')(pairs_json)
            else:
                return None
        except Exception as e:
            return None
        return wps
    async def save(self, guild):
        filename = getattr(type(self), 'filename')
        channame = getattr(type(self), 'channame')
        channel = discord.utils.get(guild.channels, name=channame)
        await channel.send(file=discord.File(fp=io.StringIO(self.to_json()), filename=filename))
