FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    CARE_DEVICE=cpu \
    CARE_INPUT_DIR=/input \
    CARE_OUTPUT_DIR=/output/myops \
    CARE_SELF_MODEL_DIR=/app/models/self_model \
    nnUNet_raw=/app/models/nnunet/nnUNet_raw \
    nnUNet_preprocessed=/app/models/nnunet/nnUNet_preprocessed \
    nnUNet_results=/app/models/nnunet/nnUNet_results

WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock

COPY care_ase_vendor/src /app/src
COPY care_ase_vendor/data /app/src/data
COPY models /app/models
COPY predict.py /app/predict.py
COPY entrypoint.sh /app/entrypoint.sh
RUN mkdir -p \
    /app/models/nnunet/nnUNet_raw \
    /app/models/nnunet/nnUNet_preprocessed \
 && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
