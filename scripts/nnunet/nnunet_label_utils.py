# Label remapping for CARE Myocardium (readme pixel values -> consecutive nnU-Net labels).
# Original: LV myocardium 200, LV blood 500, RV blood 600, edema 1220, scar 2221 or 1.

RAW_TO_NNUNET = {
    0: 0,
    200: 1,
    500: 2,
    600: 3,
    1220: 4,
    2221: 5,
    1: 5,
}

NNUNET_TO_NAME = {
    0: "background",
    1: "myocardium",
    2: "LV_blood",
    3: "RV_blood",
    4: "edema",
    5: "scar",
}


def remap_segmentation(arr):
    """Map raw label volume to uint8 0..5. Unknown values become 0."""
    import numpy as np

    a = np.asarray(arr).astype(np.int32, copy=False)
    out = np.zeros_like(a, dtype=np.uint8)
    for raw, nid in RAW_TO_NNUNET.items():
        out[a == raw] = nid
    return out


def labels_dict_for_dataset_json():
    return {name: i for i, name in NNUNET_TO_NAME.items()}


def labels_dict_for_ids(ids):
    """
    Build dataset.json labels from a subset of nnU-Net IDs.
    Always keeps background (0) first.
    """
    keep = {int(i) for i in ids}
    keep.add(0)
    ordered = [i for i in sorted(NNUNET_TO_NAME.keys()) if i in keep]
    return {NNUNET_TO_NAME[i]: i for i in ordered}
