FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend

EXPOSE 8000

# Seeding is a separate step (make seed) so the image stays stateless.
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
