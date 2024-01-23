FROM python:3.10

ENV DASH_DEBUG_MODE False
COPY . .
WORKDIR .
RUN set -ex && \
    pip install -r requirements.txt
EXPOSE 5000


CMD ["python", "asteroid_data_processing.py"]
