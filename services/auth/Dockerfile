FROM python:3.11-slim

WORKDIR /app

COPY ./requirements-base.txt .
RUN pip install --no-cache-dir -r requirements-base.txt

COPY ./services/auth/requirements.txt ./requirements-local.txt
RUN pip install --no-cache-dir -r requirements-local.txt

COPY ./services/auth .

# без этой хуйни хацкеры могут делать бобо
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["sh", "-c", "\
  if [ \"$RUN_MIGRATIONS\" = \"true\" ]; then \
    echo \"Running migrations...\" && \
    alembic upgrade head; \
  fi && \
  uvicorn main:app \
    --host ${HOST:-0.0.0.0} \
    --port ${PORT:-8000} \
    --reload ${RELOAD:+--reload}\
"]
