from enum import Enum

import os,discord,threading,asyncio

from discord.ext import commands

#import whisper

#model = whisper.load_model("base")

#Use Whisper to convert recorded audio files to text
def convert_audio_to_text()->str:
    result = model.transcribe("audio.mp3")
    #print(result["text"])
    return result[text]


connections = {}

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("."),
    description="I'm a bot",
    intents=intents,
)

class Sinks(Enum):
    mp3 = discord.sinks.MP3Sink()
    wav = discord.sinks.WaveSink()
    pcm = discord.sinks.PCMSink()
    ogg = discord.sinks.OGGSink()
    mka = discord.sinks.MKASink()
    mkv = discord.sinks.MKVSink()
    mp4 = discord.sinks.MP4Sink()
    m4a = discord.sinks.M4ASink()


async def finished_callback(sink, channel: discord.TextChannel, *args):
    recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
    await sink.vc.disconnect()

    for user_id, audio in sink.audio_data.items():
        #print(f"Audio file location was {audio.file} {user_id}.{sink.encoding}")
        with open(f"{user_id}.{sink.encoding}", "wb") as f:
            f.write(audio.file.getbuffer())

    files = [
        discord.File(audio.file, f"{user_id}.{sink.encoding}")
        for user_id, audio in sink.audio_data.items()
    ]
    await channel.send(
        f"Finished! Recorded audio for {', '.join(recorded_users)}.", files=files
    )


#@bot.slash_command()
#async def hello(ctx, name: str = None):
#    name = name or ctx.author.name
#    await ctx.respond(f"Hello {name}!")

@bot.command()
async def add(ctx: commands.Context, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(str(left + right))

@bot.command()
async def hello(ctx, name: str = None):
    name = name or ctx.author.name
    await ctx.send(f"Hello {name} {ctx.author.id}!")

@bot.command()
async def record(ctx):
    voice = ctx.author.voice

    if not voice:
        return await ctx.send("You're not in a vc right now")

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc})

    print("Starting record command")
    vc.start_recording(
        discord.sinks.WaveSink(),
        finished_callback,
        ctx.channel,
    )

    #timer = threading.Timer(5.0, stop, args=[ctx])
    #timer.start()
    await asyncio.sleep(5)
    await stop(ctx)
    
    await ctx.send("The recording has started!")

@bot.slash_command()
async def vc(ctx):
    record(ctx)

@bot.command()
async def stop(ctx: discord.ApplicationContext):
    """Stop recording."""
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording()
        del connections[ctx.guild.id]
        #await ctx.delete()
    else:
        await ctx.send("Not recording in this guild.")

bot.run(os.getenv('DISCORD_BOT_TOKEN'))
