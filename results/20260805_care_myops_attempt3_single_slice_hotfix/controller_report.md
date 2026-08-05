组织方失败原因已被定位为合法单层输入在 nnU-Net 重采样尺寸计算中被 round 成 0，修复只是在该尺寸计算后加最小 1 voxel 保护；这会避免 Docker 因 depth=1 输入整批崩溃，同时不改变正常病例输出。所有模型资产和推理配置保持原 Attempt 3 不变，15 个正常 public MyoPS case 对修复前后逐数组 bitwise exact；服务器只做静态复核，没有运行 Docker。下一步只应由人工把草稿内容发给组织方；本任务未发送组织方邮件，也未上传任何 challenge 或 validation predictions。

controller_verification_decision: `VERIFIED_COMPLETE`

## Scope

- Task: `20260805_care_myops_attempt3_single_slice_hotfix`
- Base archive: `MyoPS-OrganAgent-attempt3.tar.gz`
- Base SHA256: `921a0115428b8d597c67d57d45862de1371bf6d3097b5dc8c9b27e7407589ef3`
- Corrected archive: `MyoPS-OrganAgent-Attempt3-corrected.tar.gz`
- Corrected SHA256: `52c39ab06abc0d1e4411def14bea445e27099ca9c13164dab67eb0e063c93709`
- Drive link: `https://drive.google.com/open?id=1Q7CExNmP5oPJ3z3PbEdiM4Kilx5onz67`

## Verification

- Original Attempt 3 crash reproduced on depth=1 synthetic input before patching.
- Corrected image retains five nnU-Net checkpoints and two CARE-ASE step500 checkpoints byte-identically.
- `selection.json`, `predict.py`, entrypoint, requirements, fold/TTA/threshold/label map/overlay/dependencies unchanged.
- Normal 15-case regression: 15/15 array, geometry, and canonical SHA exact.
- Synthetic matrix, mixed batch, synthetic determinism, and clean save/load full synthetic plus 3 normal sentinel all passed.
- Failure-mode matrix passed with geometry mismatch documented as inherited nonblocking base behavior.
- Server audit files under `results/20260805_care_myops_attempt3_single_slice_hotfix_server_audit/` passed static checks only.

## Boundary

- CineMyoPS was not rebuilt.
- Organizer reply is a draft only: `organizer_reply_draft.md`.
- No organizer email was sent.
- No challenge or validation predictions were uploaded.
