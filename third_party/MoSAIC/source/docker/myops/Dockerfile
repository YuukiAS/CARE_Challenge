FROM python:3.10-slim

RUN pip install --no-cache-dir \
    torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    numpy nibabel scipy SimpleITK pyyaml

COPY myops_pkg /app/myops_pkg
COPY configs /app/configs
COPY weights /app/weights
COPY predict.py /app/predict.py

WORKDIR /app
ENTRYPOINT ["python", "/app/predict.py"]
