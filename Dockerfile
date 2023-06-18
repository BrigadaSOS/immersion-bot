FROM python:3.10

COPY requirements.txt /app/

WORKDIR /app
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "launch_bot.py"]
