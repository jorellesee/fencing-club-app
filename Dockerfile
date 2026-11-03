FROM python:3.12-slim

# Print logs straight away, and don't litter the image with .pyc files.
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Requirements first: Docker caches this layer, so a code-only change skips pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hashed static files for WhiteNoise. The key is a placeholder: the real one is set at run time.
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 8000

# The volume is mounted by now, so migrate the real database, then serve.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]
