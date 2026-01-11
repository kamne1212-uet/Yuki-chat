FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Yuki-chat_bot /app/Yuki-chat_bot

CMD ["python", "-u", "Yuki-chat_bot/bot.py"]
