# CARE-ASE outer diagnostic step13000/12000 vs old step5000/4000

这是用户授权的 held-out outer diagnostic，不是 checkpoint selection，也不是 early stop 依据。

| 口径 | n old | CARE old | nnUNet old | delta old | n new | CARE new | nnUNet new | delta new | CARE变化 | delta变化 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all outer scar | 88 | 0.450878 | 0.556261 | -0.105383 | 88 | 0.398799 | 0.556291 | -0.157491 | -0.052078 | -0.052108 |
| complete tri-modal scar / T2-present | 32 | 0.679285 | 0.672459 | 0.006826 | 32 | 0.647789 | 0.672544 | -0.024756 | -0.031496 | -0.031582 |
| partial/no-T2 scar | 56 | 0.320360 | 0.489863 | -0.169503 | 56 | 0.256520 | 0.489860 | -0.233340 | -0.063840 | -0.063837 |
| pure edema / T2-present | 32 | 0.450331 | 0.475130 | -0.024799 | 32 | 0.472279 | 0.475188 | -0.002909 | 0.021948 | 0.021890 |
| CenterB complete scar | 14 | 0.668708 | 0.708964 | -0.040256 | 14 | 0.661872 | 0.709156 | -0.047283 | -0.006836 | -0.007028 |
| CenterC complete scar | 18 | 0.687511 | 0.644065 | 0.043446 | 18 | 0.636835 | 0.644069 | -0.007234 | -0.050676 | -0.050680 |
| CenterB edema | 14 | 0.523760 | 0.571075 | -0.047315 | 14 | 0.559932 | 0.571126 | -0.011194 | 0.036172 | 0.036121 |
| CenterC edema | 18 | 0.393219 | 0.400507 | -0.007288 | 18 | 0.404104 | 0.400570 | 0.003534 | 0.010885 | 0.010822 |

| 口径 | fold | CARE old | CARE new | CARE变化 | delta old | delta new | delta变化 | empty old->new | help/harm old | help/harm new |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all outer scar | fold2 | 0.529509 | 0.578410 | 0.048900 | -0.061280 | -0.012396 | 0.048884 | 1->1 | 16/25 | 19/22 |
| all outer scar | fold3 | 0.372246 | 0.219189 | -0.153057 | -0.149487 | -0.302587 | -0.153100 | 10->28 | 10/32 | 7/34 |
| all outer scar | combined | 0.450878 | 0.398799 | -0.052078 | -0.105383 | -0.157491 | -0.052108 | 11->29 | 26/57 | 26/56 |
| complete tri-modal scar / T2-present | fold2 | 0.704129 | 0.692807 | -0.011322 | 0.006164 | -0.005206 | -0.011371 | 0->0 | 11/5 | 10/6 |
| complete tri-modal scar / T2-present | fold3 | 0.654441 | 0.602771 | -0.051670 | 0.007488 | -0.044305 | -0.051793 | 2->0 | 8/8 | 7/8 |
| complete tri-modal scar / T2-present | combined | 0.679285 | 0.647789 | -0.031496 | 0.006826 | -0.024756 | -0.031582 | 2->0 | 19/13 | 17/14 |
| partial/no-T2 scar | fold2 | 0.429727 | 0.513040 | 0.083313 | -0.099820 | -0.016504 | 0.083316 | 1->1 | 5/20 | 9/16 |
| partial/no-T2 scar | fold3 | 0.210992 | 0.000000 | -0.210992 | -0.239187 | -0.450176 | -0.210989 | 8->28 | 2/24 | 0/26 |
| partial/no-T2 scar | combined | 0.320360 | 0.256520 | -0.063840 | -0.169503 | -0.233340 | -0.063837 | 9->29 | 7/44 | 9/42 |
| pure edema / T2-present | fold2 | 0.507419 | 0.504119 | -0.003300 | 0.000928 | -0.002458 | -0.003386 | 0->0 |  |  |
| pure edema / T2-present | fold3 | 0.393242 | 0.440439 | 0.047197 | -0.050527 | -0.003360 | 0.047166 | 1->0 |  |  |
| pure edema / T2-present | combined | 0.450331 | 0.472279 | 0.021948 | -0.024799 | -0.002909 | 0.021890 | 1->0 |  |  |

Key read: fold2 scar improves, fold3 partial/no-T2 scar remains collapsed, combined edema is approximately matched but slightly below nnU-Net at this latest outer pair.
