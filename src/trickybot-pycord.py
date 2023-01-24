from enum import Enum

import os,discord,threading,asyncio

from discord.ext import commands

from discord import Message as DiscordMessage
import logging
from base import Message, Conversation
from constants import (
    BOT_INVITE_URL,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
    ACTIVATE_THREAD_PREFX,
    MAX_THREAD_MESSAGES,
    SECONDS_DELAY_RECEIVING_MSG,
)
import asyncio
from utils import (
    logger,
    should_block,
    close_thread,
    is_last_message_stale,
    discord_message_to_message,
)
import completion
from completion import generate_completion_response, process_response, process_text_response
from moderation import (
    moderate_message,
    send_moderation_blocked_message,
    send_moderation_flagged_message,
)

logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
)

import pyttsx3

# Initialize the text-to-speech engine
engine = pyttsx3.init(driverName='sapi5')

def initialize_text_to_speech():
    text = "Hello, my name is trickybot. I am an artificial intelligence designed to interact with users in this channel"

    print(f"Voices are {engine.getProperty('voices')}")

    # Set the volume and rate of speech
    engine.setProperty('volume', 1.0)
    engine.setProperty('rate', 150)

    #Use Cortana (Microsoft EVA)
    engine.setProperty('voice',"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_enUS_EvaM")

def text_to_speech(text:str)->str:

    output_file = "speech.mp3"

    #Save the audio to a file
    engine.save_to_file(text, output_file)
    #engine.say(text)
    engine.runAndWait()

    return output_file

import whisper

model = whisper.load_model("base")

#Use Whisper to convert recorded audio files to text
def convert_audio_to_text(filename:str)->str:
    result = model.transcribe(filename)
    print(f"Whisper result: {result['text']}")
    return result['text']

#Retain a dictionary of messages for all users
messages = []
connections = {}

intents = discord.Intents.all()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("."),
    description="I'm a bot",
    intents=intents,
)

import replicate

model = replicate.models.get("stability-ai/stable-diffusion")
version = model.versions.get("f178fa7a1ae43a9a9af01b833b9d2ecf97b1bcb0acfd2dc5dd04895e042863f1")

@bot.slash_command()
async def generate(ctx, prompt: str = None):

    #await ctx.send(f"Generating image for prompt: {prompt}")

    await ctx.send(f'Generating prompt: {prompt}')

    await ctx.defer()

    # https://replicate.com/stability-ai/stable-diffusion/versions/f178fa7a1ae43a9a9af01b833b9d2ecf97b1bcb0acfd2dc5dd04895e042863f1#input
    inputs = {
        # Input prompt
        'prompt': f"{prompt}",

        # Specify things to not see in the output
        # 'negative_prompt': ...,

        # Width of output image. Maximum size is 1024x768 or 768x1024 because
        # of memory limits
        'width': 768,

        # Height of output image. Maximum size is 1024x768 or 768x1024 because
        # of memory limits
        'height': 768,

        # Prompt strength when using init image. 1.0 corresponds to full
        # destruction of information in init image
        'prompt_strength': 0.8,

        # Number of images to output.
        # Range: 1 to 4
        'num_outputs': 1,

        # Number of denoising steps
        # Range: 1 to 500
        'num_inference_steps': 50,

        # Scale for classifier-free guidance
        # Range: 1 to 20
        'guidance_scale': 7.5,

        # Choose a scheduler.
        'scheduler': "DPMSolverMultistep",

        # Random seed. Leave blank to randomize the seed
        # 'seed': ...,
    }

    # https://replicate.com/stability-ai/stable-diffusion/versions/f178fa7a1ae43a9a9af01b833b9d2ecf97b1bcb0acfd2dc5dd04895e042863f1#output-schema

    try:
        output = version.predict(**inputs)
        print(output)
        await ctx.followup.send(f"Successfully generated image for prompt: {prompt} {output[0]}")        
    except discord.errors.ApplicationCommandInvokeError as e:
        await ctx.followup.send(f"Error: {e}")
    except: await ctx.followup.send(f"Image generation returned an error or violated content filter.")


class Sinks(Enum):
    mp3 = discord.sinks.MP3Sink()
    wav = discord.sinks.WaveSink()
    pcm = discord.sinks.PCMSink()
    ogg = discord.sinks.OGGSink()
    mka = discord.sinks.MKASink()
    mkv = discord.sinks.MKVSink()
    mp4 = discord.sinks.MP4Sink()
    m4a = discord.sinks.M4ASink()


def add_to_messages(user, text:str):
    #If the user isn't in the dictionary, initialize a list of messages for them
    #if not user.id in messages:
    #    messages[user] = []

    #Handle a special case of adding messages for the bot
    if user=="trickybot":    
        messages.append(Message(user = "trickybot", text=text))
        return

    #Otherwise get the discord user's name
    messages.append(Message(user = user.name, text=text))


async def send_to_model(user):    
    try:
        # generate the response

        print(f"Messages were: {messages}")

        #async with thread.typing():
        response_data = await generate_completion_response(
        messages=messages, user=user
        )    

        # send response
        text_response,status_response=await process_text_response(
            user=user, response_data=response_data
        )
        return text_response,status_response
    except Exception as e:
        logger.exception(e)

async def finished_callback(sink, channel: discord.TextChannel, context, *args):
    recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
    #await sink.vc.disconnect()

    for user_id, audio in sink.audio_data.items():
        #print(f"Audio file location was {audio.file} {user_id}.{sink.encoding}")

        #Write to a file
        with open(f"{user_id}.{sink.encoding}", "wb") as f:
            f.write(audio.file.getbuffer())

        #Convert to text using whisper
        converted_text = convert_audio_to_text(f"{user_id}.{sink.encoding}") # "Trickybot, what's the capital of Idaho?"#

        #Get the user from the provided ID        
        user = bot.get_user(user_id)
        print(f"User was {user.name} and text was {converted_text}")

        await context.send(f"Interpreted speech: {converted_text}")

        #Add the user prompt to the conversation history
        add_to_messages(user, converted_text)

        #Send the converted text to the model
        ai_response = await send_to_model(user)

        print(f"AI response was {ai_response}")
        await context.send(f"AI Response: {ai_response[0]}")

        #Add the response text from the ai
        add_to_messages("trickybot", ai_response[0])

        #Convert the AI response to an audio file
        text_to_speech(ai_response[0])

        #Play the response in the current voice channel
        await play(context, "speech.mp3")


    #files = [
    #    discord.File(audio.file, f"{user_id}.{sink.encoding}")
    #    for user_id, audio in sink.audio_data.items()
    #]
    #await channel.send(
    #    f"Finished! Recorded audio for {', '.join(recorded_users)}.", files=files
    #)


#@bot.slash_command()
#async def hello(ctx, name: str = None):
#    name = name or ctx.author.name
#    await ctx.respond(f"Hello {name}!")

#@commands.command()
async def play(ctx: commands.Context, query: str):
    """Plays a file from the local filesystem"""

    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
    ctx.voice_client.play(
        source, after=lambda e: print(f"Player error: {e}") if e else None
    )

    #await ctx.send(f"Now playing: {query}")

@bot.command()
async def add(ctx: commands.Context, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(str(left + right))

@bot.command()
async def hello(ctx, name: str = None):
    name = name or ctx.author.name
    await ctx.send(f"Hello {name} {ctx.author.id}!")

async def timer(ctx, seconds_to_listen):
    await asyncio.sleep(seconds_to_listen)
    await stop(ctx)

@bot.command()
async def ask(ctx, seconds_to_listen=4):
    voice = ctx.author.voice

    if not voice:
        return await ctx.send("You're not in a vc right now")

    vc = discord.utils.get(bot.voice_clients, guild=ctx.guild)


    if not vc:
        vc = await voice.channel.connect()
    
    connections.update({ctx.guild.id: vc})

    #await play(ctx, "speech.mp3")

    print("Starting record command")
    vc.start_recording(
        discord.sinks.WaveSink(),
        finished_callback,
        ctx.channel,
        ctx
    )

    #await asyncio.sleep(5)
    #await stop(ctx)
    
    task = asyncio.create_task(timer(ctx,seconds_to_listen))

    #await ctx.send("The recording has started!")
    await task

@bot.command(description="Ask the bot a question.")
async def vc(ctx):
    ask(ctx)

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

@bot.event
async def on_ready():
    initialize_text_to_speech()
    print("I am online")

bot.run(DISCORD_BOT_TOKEN)#os.environ.get('DISCORD_BOT_TOKEN'))
