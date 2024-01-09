FROM python:3.9

WORKDIR /asteroidapp

COPY . /asteroidapp

RUN pip install -r requirements.txt


EXPOSE 3000
CMD ["python", "asteroid_data_processing.py"]
CMD ["python", "asteroid_visualisation.py"]


