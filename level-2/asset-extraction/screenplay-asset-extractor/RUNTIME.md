# 运行环境

插件不依赖电脑当前目录或全局 Python 包。所有脚本应通过 `scripts/launch.py` 启动；它会优先使用插件目录 `.venv`，其次使用按 `requirements.lock` 指纹隔离的用户缓存运行时。

首次使用：

```bash
python3 scripts/bootstrap.py --install
python3 scripts/launch.py scripts/env_diagnostics.py
```

诊断必须显示 Python 3.12+，并能导入 `jsonschema`、`PyYAML`、`python-docx`、`openpyxl`、`lxml`。不要依赖 `PATH` 中的 `python` 别名、当前工作目录或其他电脑上的同名 Skill。
