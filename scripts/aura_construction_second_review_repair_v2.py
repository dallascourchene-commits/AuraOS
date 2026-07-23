#!/usr/bin/env python3
"""Run the bounded second-review repair with the corrected frame lookup rule."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("aura_construction_second_review_repair.py")
source = SOURCE.read_text(encoding="utf-8")
old = '''    frame_lookup = (
        "                    next(item.frame_id for item in storeys if item.storey_id == package.storey_id),\\n"
    )
    if "                    package_frame_id,\\n" not in text:
        count = text.count(frame_lookup)
        if count != 2:
            raise RuntimeError(f"package frame lookup: expected two spans, found {count}")
        print("repairing: package frame consumers")
        text = text.replace(frame_lookup, "                    package_frame_id,\\n", 2)
'''
new = '''    frame_expression = "next(item.frame_id for item in storeys if item.storey_id == package.storey_id)"
    if frame_expression in text:
        count = text.count(frame_expression)
        print(f"repairing: {count} remaining package frame consumers")
        text = text.replace(frame_expression, "package_frame_id")
'''
if old not in source:
    raise SystemExit("repair source frame-lookup span is missing")
source = source.replace(old, new, 1)
namespace = {"__name__": "__main__", "__file__": str(SOURCE)}
exec(compile(source, str(SOURCE), "exec"), namespace)
