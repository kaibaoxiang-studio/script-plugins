#!/usr/bin/env python3
import importlib.util, json, platform, sys
mods={'jsonschema':'jsonschema','yaml':'PyYAML','docx':'python-docx','openpyxl':'openpyxl','lxml':'lxml'}
print(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'modules':{m:bool(importlib.util.find_spec(m)) for m in mods}},ensure_ascii=False,indent=2))
if sys.version_info<(3,12) or not all(importlib.util.find_spec(m) for m in mods): raise SystemExit(1)
