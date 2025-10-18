web: gunicorn plutus.wsgi:application --log-file - --log-level debug --limit-request-line 8190 --worker-class gthread --workers 3 --threads 2 --max-requests 500 --max-requests-jitter 300 --timeout 90 --graceful-timeout 90 --worker-tmp-dir /dev/shm
release: python manage.py migrate
worker: celery -A plutus worker -l info --concurrency=1
