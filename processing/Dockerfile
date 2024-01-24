FROM python:3.10

ENV DASH_DEBUG_MODE False
COPY . .
WORKDIR .
RUN set -ex && \
    pip install -r requirements.txt
EXPOSE 5000


CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "asteroid_data_processing:app"]