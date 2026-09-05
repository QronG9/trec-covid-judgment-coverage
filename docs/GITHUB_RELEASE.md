# 我的 GitHub 发布版本

我将这套实验整理为 **v2.0.0**。推荐仓库名为 `trec-covid-judgment-coverage`。

仓库简介可用：`My TREC-COVID document-selection experiments: 12 configurations, pilot-to-full-query tracking, and offline reproducible evaluation.`

这个版本包含我的第一人称研究报告、12 个完整 50 查询配置、8 个初始 5 查询
配置、2 个非空摘要条件、原始标签、结果表、图、测试及来源记录。

## 发布步骤

我先在 GitHub 创建空仓库并选择可见性，然后在本地仓库根目录连接 GitHub
提供的地址：

```bash
git remote add origin <GitHub 提供的仓库地址>
git push -u origin main
git push origin v2.0.0
```

这些是准备好的发布步骤；当前交付的是本地仓库和上传压缩包。
本地仓库保留阶段历史，`git archive` 生成的
`trec-covid-judgment-coverage-v2.0.0-github.zip` 只包含 v2.0.0 的公开文件。

我使用 `.gitignore` 将本地历史备份、文章全文、向量缓存和虚拟环境留在本地。
从 Git 推送或使用提供的上传包，可以获得同一组已验证的公开文件。

## 我的版本摘要

我从 5 个查询开始，扩展到 50 个查询，再比较融合、随机子集、MMR、查询扩展、
learned sparse、第二个 dense 模型和 cross-encoder 重排。我分别记录判断覆盖、
观察相关性指标、与 BM25 的集合重合及固定排名下的 precision 界限，并用两组
保持候选集合的实验对照检查“选择集合”和“改变前缀顺序”的关系。

GitHub Actions 在上传后的 push、pull request 和手动触发时执行结果复算。
本地验证步骤及实际结果见 [RELEASE_VALIDATION](../provenance/RELEASE_VALIDATION.md)。

