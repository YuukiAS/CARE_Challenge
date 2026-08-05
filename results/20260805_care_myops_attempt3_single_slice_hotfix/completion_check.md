这次 Attempt 3 MyoPS 单层输入热修复已经达到操作闭合：失败已在原镜像复现，修复只包含 `np.maximum(new_shape, 1)`，正常病例输出不变，边界输入通过，archive 已重新保存、上传、公开链接检查并完成服务器静态审计。CineMyoPS 未重建是任务边界，组织方邮件未发送，challenge/validation predictions 未上传。

## Checklist

- Attempt 3 original archive uniquely identified: `PASS`
- Attempt 2 archive not used: `PASS`
- Original depth=1 zero-dimension crash reproduced: `PASS`
- Only allowed code change applied: `PASS`
- Five nnU-Net checkpoints unchanged: `PASS`
- Two CARE-ASE step500 checkpoints unchanged: `PASS`
- `selection.json`, `predict.py`, entrypoint, requirements, fold/TTA/threshold/label/overlay unchanged: `PASS`
- Base and corrected 15-case normal inference bitwise exact: `PASS`
- depth1/depth2 synthetic matrix: `PASS`
- 15 normal plus synthetic mixed batch: `PASS`
- synthetic determinism: `PASS`
- clean save/load full synthetic plus 3 normal sentinel: `PASS`
- corrected archive, SHA256SUMS, new Drive public link: `PASS`
- server static audit only, no Docker on server: `PASS`
- CineMyoPS not rebuilt: `PASS`
- organizer email sent: `false`
- challenge or validation predictions uploaded: `false`

controller_verification_decision: `VERIFIED_COMPLETE`
