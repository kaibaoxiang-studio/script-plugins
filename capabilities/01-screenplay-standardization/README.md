# 01｜剧本标准化

**当前状态：解析器可运行；无损标准化尚未完成。**

scripts/normalize_screenplay.py 与 analysis_provenance.py 来自上游 ai-script-breakdown。支持 TXT、Markdown、Fountain、FDX 文本输入，输出场景映射 JSON、来源位置、人物和地点线索、提取警告。PDF/DOCX 必须先用版面感知工具提取并核对文本，不能直接交给该脚本。

使用 Python 3.12+，从仓库根目录运行：

    python3.12 capabilities/01-screenplay-standardization/scripts/normalize_screenplay.py \
      /path/to/script.fountain --source-id script-001 --draft-id draft-001 \
      --output /tmp/script-scenes.json

**边界：**脚本会统一 Unicode、换行和行尾空白，哈希针对整理后的文本；当前没有原始字节哈希、可逆映射或逐字一致性验收。其 JSON 是解析中间物，**不是**团队已定义的一级“标准化剧本”，也不能直接作为 03/04 所需的完整 screenplay_breakdown_v1。可借鉴的证据规则见 [format-and-evidence.md](references/format-and-evidence.md)。

SN2S 的评估见 [sn2s-assessment.md](references/sn2s-assessment.md)。
