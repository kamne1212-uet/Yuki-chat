# Yuki Chat Bot

Discord bot powered by Llama3 via Ollama.

## Features

-  **AI Chat**: Powered by Llama3 8B (instruct model) via Ollama
-  **Memory**: Powered by three layers of models, each handling a separate memory task, this system helps capture context effectively and maintain long-term memory
-  **Message History**: SQLite-based conversation history
-  **Character Roleplay**: Plays as Yuki Suou from Roshidere anime
-  **Contextual GIFs**: Sends relevant GIFs based on conversation context
-  **Rate Limiting**: Built-in anti-spam protection

## Setup

### Prerequisites

- Docker and Docker Compose
- Discord Bot Token

### Installation

1. Clone the repository
2. Create .env file and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Pull the required Ollama models (first time only):
   ```bash
   docker exec -it yuki-chat_llma3-ollama-1 ollama pull llama3:8b-instruct-q4_K_M
   docker exec -it yuki-chat_llma3-ollama-1 ollama pull nomic-embed-text
   docker exec -it yuki-chat_llma3-ollama-1 ollama pull qwen2:1.5b
   docker exec -it yuki-chat_llma3-ollama-1 ollama pull phi3:mini
   ```

## Usage

- **Mention the bot**: `@Yuki your message here`
- **Slash command (INCOMPLETED)**: `/ask question: your question here`

## Project Structure

```
Yuki-chat_bot/
├── bot.py              # Main Discord bot
├── ai/
│   ├── engine.py       # LLM streaming interface
│   ├── memory_manager.py  # Memory orchestration
│   ├── sqlite_memory.py   # SQLite message storage
│   ├── sematic_memory.py  # Semantic/vector memory
│   ├── embeddings.py      # Embedding generation
│   ├── antispam.py        # Rate limiting
│   ├── gif_manager.py     # Contextual GIF logic
│   └── prompts.py         # Persona prompts
├── data/               # Database files (auto-created)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuration

- **Chat Model**: `llama3:8b-instruct-q4_K_M` (can be changed in `ai/engine.py`)
- **Embed model**: `nomic-embed-text` (can be changed in `ai/engine.py`)
- **Yuki's answer summary model**: `phi3:mini` (can be changed in `ai/engine.py`)
- **Conversation summary model**: `qwen2:1.5b` (can be changed in `ai/engine.py`)
- **Max Tokens**: 256 (can be adjusted in `ai/engine.py`)
- **Rate Limit**: 30 seconds cooldown per user
- **GIF Cooldown**: 90 seconds per user

## Notes

- The bot requires Ollama to be running and accessible at `http://ollama:11434`
- Database files are stored in `./data/` directory
- Semantic memories are limited to 50 per user (auto-cleanup)

## Hardware requirements 
- **RAM**: 18GB at least
- **CPU**: 12 cores at least
- **GPU**: Recommended
