FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    CARE_DEVICE=cpu

WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock

COPY configs /app/configs
COPY vendor /app/vendor
COPY predict.py /app/predict.py
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
