# Cine Temporal Failure Interpretation

This preflight uses existing frozen CineMA anatomy predictions. It can test whether keyframe anatomy context improves frame0 myocardium/LV proxies, but it cannot validate scar because the source anatomy prior has no scar head.

If temporal variants underperform the reference control, the likely mechanisms are: nonreference features are not motion-registered into the ED/reference frame; frame agreement favors the reference frame too strongly; and the current keyframe selection was produced by the previous adapter rather than an optimized motion descriptor.
