import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

from ai.engine import stream_answer_summary_llm
from ai.engine import stream_convo_summary_llm
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

        async for _ in stream_answer_summary_llm("Hello"):
            break

        print("All models warmed up~")
    except Exception as e:
        print("Warmup error:", e)


async def _generate_summary_background(user_id: str):
    """Background task to generate conversation summary"""
    try:
        await memory.generate_summary_async(user_id, stream_convo_summary_llm)
        print(f"Summary generated for user {user_id}")
    except Exception as e:
        print(f"Error generating summary for user {user_id}: {e}")


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

    try:
        async with channel.typing():
            async for chunk in stream_llm(messages):
                if chunk and chunk.strip():
                    full += chunk
    except Exception as e:
        print(f"Error during streaming: {e}")
        await channel.send("Sorry~ something went wrong. Can you try again?")
        return

    full = full.strip()
    if not full:
        await channel.send("Sorry~ can you ask again?")
        return

    # ===== SEND FULL REPLY TO USER (INSTANTLY) =====
    for i in range(0, len(full), 2000):
        if isinstance(source, discord.Message):
            await channel.send(
                full[i:i+2000],
                reference=source,
                mention_author=True
            )
        else:
            await channel.send(full[i:i+2000])

    # ===== SAVE YUKI SUMMARY (BACKGROUND) =====
    asyncio.create_task(
        memory.add_Yuki_message(
            user_id=user_id,
            full_content=full,
            summarize_llm_func=stream_answer_summary_llm
        )
    )

    # ===== CONTEXTUAL GIF =====
    if can_send_gif(str(user_id)):
        gif = pick_gif_from_reply(full)
        if gif:
            await channel.send(gif)

    # ===== AUTO SUMMARIZATION (LONG-TERM) =====
    if memory.should_summarize(user_id, threshold=2020):
        message_count = memory.count_messages(user_id)
        existing_summary = memory.get_summary(user_id)

        should_create = (
            not existing_summary or
            (message_count % 20 == 0 and message_count >= 20)
        )

        if should_create:
            asyncio.create_task(
                _generate_summary_background(user_id)
            )


# ====== SLASH COMMAND ====== (Incompleted)
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


