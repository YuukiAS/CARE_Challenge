FROM care-myocardium-myops:attempt3-failed-base

COPY apply_single_slice_hotfix.py /tmp/apply_single_slice_hotfix.py

RUN python /tmp/apply_single_slice_hotfix.py \
 && rm /tmp/apply_single_slice_hotfix.py

LABEL org.opencontainers.image.description="CARE MyoPS Attempt3 single-slice preprocessing hotfix"
