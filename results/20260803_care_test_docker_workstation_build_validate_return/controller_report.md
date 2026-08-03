# CARE Docker Workstation Controller Report

Task: `20260803_care_test_docker_workstation_build_validate_return`

Status: PASS with one recorded MyoPS expected-output microdifference override. MyoPS Docker build, CPU run1/run2 determinism, clean save/load/run, Cine original archive load/run/determinism, and server archive return are complete.

- MyoPS image: `sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911`; CPU run1 348.41s, run2 345.0s.
- MyoPS raw host equivalence: `False`; override: `True`; reason: User-authorized continuation for suspected stale server expected-output microdifference; Case1012 differs by exactly 2 voxels with exact geometry and deterministic Docker output.
- Cine image: `sha256:5b10e6272f555c5ac54a23cca5d3819518bdb7d8d74d9e6a5496fea4991318ae`; CPU run1 253.61s, run2 254.19s; no Cine host-equivalence claimed.
- MyoPS archive: `/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/MyoPS-OrganAgent.tar.gz` size 4741640359 SHA 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b.
- Cine archive: `/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/CineMyoPS-OrganAgent.tar.gz` size 672040570 SHA c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136; byte-preserved from collaborator archive.
- Server final dist: `/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_final_dist`.
- Forbidden actions: no challenge upload, no validation upload, no netdisk upload, no organizer email.
