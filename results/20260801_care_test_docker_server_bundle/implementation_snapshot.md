# Implementation Snapshot

The server-side task was redirected away from Docker/rootless execution. The new controller prompt was saved under `prompts/tasks/20260801_care_test_docker_server_bundle_controller.md`, the existing GPU allocation `61220581` was reused with `srun --overlap`, and frozen nnU-Net 5-fold inference was rerun for Case1001-Case1015. The fresh outputs matched historical package A geometry for all cases but did not match arrays for 11 of 15 cases, so the contract forbids MyoPS executable bundle generation and forbids `SERVER_BUNDLE_READY.json`.

MoSAIC replay was started as diagnostic evidence using the frozen Docker-recipe weights and runtime output directory. Docker, rootless Docker, Podman, Buildah, Apptainer, sudo, cloud upload, organizer email, validation upload, and new training were not used.
