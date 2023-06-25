FROM python:3.10

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY immersion_bot/ immersion_bot/
CMD ["python3", "immersion_bot/launch_bot.py"]
