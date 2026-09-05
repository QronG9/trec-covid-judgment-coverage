# 我的来源与版本记录

我以项目内相对路径、原始文件哈希和逐项参考值连接各阶段的实验。当前研究报告
覆盖 12 个全查询配置、初始五查询材料与两个非空摘要条件。

| 记录 | 我保留的内容 |
|---|---|
| [source_state.json](source_state.json) | 来源项目 HEAD、冻结标签与本版实验范围 |
| [source_inventory.csv](source_inventory.csv) | 打包时原项目 246 个已跟踪 / 暂存文件的相对路径和 SHA-256 |
| [original_freeze_verification.json](original_freeze_verification.json) | 原冻结清单中 72 个文件的哈希核对 |
| [source_preservation_check.json](source_preservation_check.json) | 原项目文件、HEAD 与暂存状态的保留检查 |
| [import_inputs.json](import_inputs.json) | 原始数据、基础排名、索引映射及非空摘要评分输入的来源 |
| [experiment_imports.json](experiment_imports.json) | 后续配置和初始五查询排名的来源、导出规则、行数与哈希 |
| [nonempty_export_validation.json](nonempty_export_validation.json) | 非空摘要条件 400 个查询 / 深度覆盖单元与保存结果的对应 |
| [reference_values.json](reference_values.json) | 三基线深入分析的 1,324 行来源参考值、2,572 项数字对照 |
| [extension_reference_values.json](extension_reference_values.json) | 全查询与初始五查询的 2,571 行参考值、7,702 项数字对照 |
| [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) | 我实际完成的发布检查及执行环境 |

两份参考值文件共提供 **3,895 行、10,274 项数字对照**。这些值从原项目已保存的
结果表提取；每条记录保留真实的历史来源文件名。新分析程序从发布的排名和
qrels 重新计算，再逐项与这些参考值比较。

我在[排名生成代码](../retrieval_source/README.md)中保留方法实现和依赖说明。
原程序按模型标识加载 checkpoint；其加载调用使用模型名。当前发布以保存的排名
及 SHA-256 固定本次计算输入，模型名称、输入长度、查询前缀和具体评分定义见
[方法说明](../docs/METHODS.md)。

`MANIFEST.sha256` 固定本版公开文件；Git 标签记录发布版本。
我将文章全文、模型缓存、虚拟环境和完整原项目历史保存在本地，公开包使用
通用排名与文本无关元数据。保存位置计数包含阶段间重复材料：初始五查询中的
五个基础配置来自全查询排名的对应子集。

准备后续版本时，我先暂存拟发布文件，再运行 `python3 scripts/build_manifest.py`，
随后执行 `python3 scripts/verify_release.py`，将验证通过的内容提交并添加新标签。
普通复算入口只读取清单和参考值，在独立临时目录产生计算结果。
