FROM care-myocardium-myops:attempt2-base

COPY apply_single_slice_hotfix.py /tmp/apply_single_slice_hotfix.py

RUN python /tmp/apply_single_slice_hotfix.py \
 && rm /tmp/apply_single_slice_hotfix.py

LABEL org.opencontainers.image.description="CARE MyoPS attempt2 single-slice preprocessing hotfix"
