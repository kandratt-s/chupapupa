FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD sh -c "if [ \"$RUN_MIGRATIONS\" = \"true\" ]; then echo \"Running migrations...\" && alembic upgrade head; fi; if [ \"$RUN_APP\" = \"true\" ]; then echo \"Starting application...\" && python main.py; fi"