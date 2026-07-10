# Cine temporal 分支

## 历史分析原文迁移

### 1.11 CineMA / Cine registration：只是诊断性 proxy，不是完整 Cine route

Cine 这条线也没有“全部实现到位”。`run_srr_v3_m7_cine_registration_repair.py` 的 docstring 明确说它是 bounded diagnostic repair attempt，读取 existing CineMyoPS safe cases 和 CineMA frame predictions，跑小规模 SimpleITK Demons non-reference registration probe；它不训练 VoxelMorph、不打包 validation、不 upload、不 promotion。

脚本里确实实现了 SimpleITK Demons 和 ANTsPy SyNOnly registration，选择 frame0 和 non-reference frames，评估 myocardium/LV Dice、HD95、NCC 等。  后续所谓 temporal dictionary 是从 cached warped segmentation proxy 构造的，核心是把 warped non-reference segmentation proxy 和 fixed frame 做 quality-weighted union / temporal proxy，并记录 CineMA label-space caveat。

这说明 CineMA 被用作 frame-wise anatomy proxy，registration 被用作 diagnostic temporal evidence；但它不是一个完整的 CineMA fine-tuned model，也不是一个端到端 cine temporal segmentation route，更不是 VoxelMorph-based motion branch。M8 review 也承认 Cine evidence 已经不只是 smoke，但仍然是 local proxy evidence，不能 claim hosted metric readiness。

所以 Cine 不能被判“路线没潜力”。当前只能说：**CineMA + registration 还停留在证据闭环/诊断 proxy 层，没有落实成最终输出模型。**

---
