FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && if [ -n \"$DJANGO_SUPERUSER_USERNAME\" ] && [ -n \"$DJANGO_SUPERUSER_PASSWORD\" ]; then python manage.py shell -c \"import os; from django.contrib.auth import get_user_model; User=get_user_model(); username=os.environ['DJANGO_SUPERUSER_USERNAME']; email=os.environ.get('DJANGO_SUPERUSER_EMAIL',''); password=os.environ['DJANGO_SUPERUSER_PASSWORD']; user,created=User.objects.get_or_create(username=username, defaults={'email':email,'role':'admin','is_staff':True,'is_superuser':True}); user.email=email; user.role='admin'; user.is_staff=True; user.is_superuser=True; user.save(); user.set_password(password); user.save(); print('Admin user created/updated successfully:', username)\"; fi && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT"]