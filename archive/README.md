# 我保留的实验历史

我按阶段保存实验，以便比较初始查询、全量查询和方法扩展的结果。
原项目文件和冻结标签保持原样；当前仓库通过保存排名和来源哈希连接这些阶段。

本地的 `archive/local-original/` 保存完整原始 Git bundle、阶段报告、输入与
输出清单、验证记录，以及非空摘要条件使用的 BM25 全库分数和查询向量。
Git bundle 包含原始项目所有分支及冻结标签。大型文档向量继续保存在原项目
的缓存位置，其 SHA-256 已记录。

```bash
git bundle verify archive/local-original/source-history.bundle
git clone archive/local-original/source-history.bundle /path/to/restored-experiments
```

本地历史目录由 `.gitignore` 保留在工作区。公开版本通过 `data/`、`results/`
和 `provenance/` 提供可直接执行的研究材料；实验阶段见
[我的研究过程](../docs/RESEARCH_PROCESS.md)。

当前 Git 仓库保留版本记录；v2.0.0 汇集全量配置与初始实验，并采用我的
第一人称研究说明。v1.0.0 与 v2.0.0 的上传压缩包分别保存。

