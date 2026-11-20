"""Preserve original replay and long-document questions without relabeling."""


def original_native(record):
    meta = record.get("_meta", {})
    return bool(meta.get("native_record") and meta.get("record_kind") in {"replay", "long"})
