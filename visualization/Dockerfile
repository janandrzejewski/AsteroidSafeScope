FROM python:3.10

ENV DASH_DEBUG_MODE False
COPY . .
WORKDIR .
RUN set -ex && \
    pip install -r requirements.txt
EXPOSE 8050


CMD ["python", "/asteroid_visualization.py"]
