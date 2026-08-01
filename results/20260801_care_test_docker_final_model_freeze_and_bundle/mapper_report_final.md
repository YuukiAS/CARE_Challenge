# Mapper Report

本次改变的是交付图和证据结构，不改变训练图。MyoPS production source splits scar from MoSAIC and anatomy/pure edema from nnU-Net, with a hard guard against MoSAIC edema weights in the MyoPS bundle. CineMyoPS production source follows the MoSAIC repo-final Cine graph with three z-spacings.

Source contexts:

- `docker/CARE2026_Myocardium/MyoPS`
- `docker/CARE2026_Myocardium/CineMyoPS`

Runtime transfer bundle:

- `/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/transfer_bundle`
- `/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/transfer/care2026_myocardium_final_model_freeze_transfer_bundle.tar.gz`
