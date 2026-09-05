# GitHub 上传准备

推荐仓库名：`trec-covid-judgment-coverage`。

推荐简介：`Partial reimplementation and judgment-coverage diagnostic on BEIR TREC-COVID, with offline reproducible results and corrected claims.`

本目录已准备独立 Git 历史、`main` 分支、v1.0.0 标签、README、研究短报告、
勘误、许可及引用信息。当前尚未创建远程仓库或上传文件。

## 上传本地仓库

先在 GitHub 创建一个空仓库，并选择自己需要的可见性；不要让 GitHub 额外
初始化 README、许可或 `.gitignore`。然后在本目录连接页面提供的仓库地址：

```bash
git remote add origin <GitHub 提供的仓库地址>
git push -u origin main
git push origin v1.0.0
```

这些命令只作为后续上传说明；本次整理没有执行远程创建或推送。
`archive/local-original/`、全文语料、下载包和本地缓存均由 `.gitignore`
排除。优先从本地 Git 仓库推送，确保只发布已经整理并验证的跟踪文件。

相邻目录提供的 `trec-covid-judgment-coverage-v1.0.0-github.zip` 是同一发布
提交的 Git 文件归档，便于转交或下载；它不含 `.git`，也不含本地历史档案。
不要把整个工作文件夹另行压缩后上传，以免混入本地保留材料。

## 版本说明

v1.0.0 固化三个方法的判断覆盖、无摘要描述与 eligibility 敏感性、共享 U 的
配对 precision 界限，以及 492 对未判断清单。正文撤回未获证据支持的机制、
模型家族、评价低估及下游扭曲主张。

GitHub Actions 配置为在后续推送和 pull request 时运行离线发布验证；首次
远程运行的结果需上传后查看。这里不把尚未执行的云端检查称为已通过。

