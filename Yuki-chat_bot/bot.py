import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from ai.engine import stream_llm
from ai.memory_manager import MemoryManager
from ai.antispam import check_rate_limit

# ====== Gifs manager ======
from ai.gif_manager import (
    pick_gif_from_reply,
    can_send_gif
)



# ====== ENV ======
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ====== BOT ======
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ====== MEMORY ======
memory = MemoryManager("data/memory.db")
SYSTEM_PROMPT = "You are the character Yuki Suou from the anime series Arya Sometimes Hides Her Feelings in Russian (Roshidere)"

@bot.event
async def on_ready():
    await tree.sync()
    await warm_up_ollama()
    print(f"Logged in as {bot.user}")

async def warm_up_ollama():
    try:
        async for _ in stream_llm(
            [{"role": "system", "content": "Hello"}]
        ):
            break
        print("I'm ready~")
    except Exception as e:
        print("Ahh...", e)


async def reply_with_stream(source, user_id: str, question: str):
    channel = source.channel if hasattr(source, "channel") else source

    memory.add_user_message(user_id, question)

    messages = memory.build_context(
        user_id=user_id,
        system_prompt=SYSTEM_PROMPT,
        query=question,
        window=8
    )

    full = ""

    async with channel.typing():
        async for chunk in stream_llm(messages):
            if chunk and chunk.strip():
                full += chunk

    full = full.strip()
    if not full:
        await channel.send("Sorry~ can you ask again?")
        return

    memory.add_assistant_message(user_id, full)

    for i in range(0, len(full), 2000):
       if isinstance(source, discord.Message):
            await channel.send(
                full[i:i+2000],
                reference=source,
                mention_author=True
        )
       else:
            await channel.send(full[i:i+2000])



    # ===== CONTEXTUAL GIF =====
    if can_send_gif(str(user_id)):
       gif = pick_gif_from_reply(full)
       if gif:
            await channel.send(gif)



# ====== SLASH COMMAND ======
@tree.command(name="ask", description="Ask Yuki")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    await reply_with_stream(
        interaction.channel,
        str(interaction.user.id),   
        question
    )

# ====== MENTION ======
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or bot.user is None:
        return

    if bot.user.mentioned_in(message):

        # Check rate limit
        if not check_rate_limit(message.author.id):
            await message.channel.send("Woah woah~ slow down")
            return

        content = (
            message.content
            .replace(f"<@{bot.user.id}>", "")
            .replace(f"<@!{bot.user.id}>", "")
            .strip()
        )

        if not content:
            await message.channel.send("What do you want~?")
            return

        await reply_with_stream(
            message,
            str(message.author.id),
            content
        )

    await bot.process_commands(message)


bot.run(TOKEN)


