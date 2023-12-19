FROM python:3.9

WORKDIR /astro/AsteroidSafeScope

COPY ./requirements.txt /astro/AsteroidSafeScope/requirements.txt

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . /astro/AsteroidSafeScope

CMD ["python", "run_scripts.py"]

