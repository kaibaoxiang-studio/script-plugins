"""只在已保存工作簿验收通过后替换目标文件。"""
import os
import tempfile
from pathlib import Path
from openpyxl import load_workbook


def save_verified(workbook, data, assets, output, approvals=None):
    from export_contract import build_plan
    from check_workbook import audit_workbook
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.asset-audit-', suffix='.xlsx', dir=output.parent)
    os.close(descriptor)
    try:
        workbook.save(temporary)
        saved = load_workbook(temporary)
        try:
            errors = audit_workbook(saved, build_plan(data, assets, approvals))
        finally:
            saved.close()
        if errors:
            raise ValueError('Excel 保存后验收失败：' + '；'.join(errors[:20]))
        os.replace(temporary, output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
