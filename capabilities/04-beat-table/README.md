# 04｜节拍表

**当前状态：已有节拍规则与结果导出；独立节拍提取节点尚未实现。**

上游 ai-script-breakdown 在完整拆解结果的 beats 字段中使用稳定节拍 ID、场景 ID、原文位置、变化及进出状态。节拍只在目标、行动、信息、权力、情绪、空间等发生实质变化时拆分；不要按台词行机械切段。见 [shared-analysis.md](references/shared-analysis.md) 与 [creative-direction.md](references/creative-direction.md)。

scripts/export_beat_table.py 从已有 breakdown.json 导出 CSV，并检查节拍引用的场景 ID；它**不会自行识别节拍**：

    python3 capabilities/04-beat-table/scripts/export_beat_table.py \
      /path/to/breakdown.json /tmp/beat-table.csv

默认仅接受覆盖状态为 completed 的拆解；需要审阅部分结果时可加 --allow-partial，导出行会携带覆盖状态。戏剧理论仅作判断镜头，参见 [theory-index.md](references/theory-index.md)。

待实现：以场记表和原文为输入的独立识别、编辑、复核及稳定 ID 延续机制。
