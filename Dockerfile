FROM python:3.8.2-slim-buster

ENV PYTHONUNBUFFERED=1

RUN apt update -y

RUN apt full-upgrade -y

RUN apt install

RUN mkdir -p /app

WORKDIR /app

ADD . /app/

RUN pip install -r requirements.txt

RUN  apt -y autoremove && apt autoclean -y


EXPOSE 80

#CMD python manage.py makemigrations && python manage.py migrate && daphne emdad.asgi:application -b 0.0.0.0 -p 8000
# CMD python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000
