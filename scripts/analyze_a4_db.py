#!/usr/bin/env python3
"""Audit RTAB-Map graph constraints and write machine-readable loop evidence."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


LINK_TYPES = {
    0: "neighbor",
    1: "global_closure",
    2: "local_space_closure",
    3: "local_time_closure",
    4: "user_closure",
    5: "virtual_closure",
    6: "neighbor_merged",
    7: "pose_prior",
    8: "landmark",
    9: "gravity",
}


def find_column(columns: list[str], candidates: tuple[str, ...]) -> str:
    by_lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in by_lower:
            return by_lower[candidate.lower()]
    raise KeyError(f"None of {candidates} found in columns {columns}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    connection = sqlite3.connect(f"file:{args.database}?mode=ro", uri=True)
    try:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        link_table = next((table for table in tables if table.lower() == "link"), None)
        if link_table is None:
            raise RuntimeError(f"Link table not found in {args.database}; tables={tables}")
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{link_table}")')]
        from_col = find_column(columns, ("from_id", "from"))
        to_col = find_column(columns, ("to_id", "to"))
        type_col = find_column(columns, ("type",))
        query = f'SELECT "{from_col}", "{to_col}", "{type_col}" FROM "{link_table}" ORDER BY "{from_col}", "{to_col}"'
        links = [
            {"from_id": int(row[0]), "to_id": int(row[1]), "type": int(row[2]), "type_name": LINK_TYPES.get(int(row[2]), "unknown")}
            for row in connection.execute(query)
        ]
        node_table = next((table for table in tables if table.lower() == "node"), None)
        node_count = int(connection.execute(f'SELECT COUNT(*) FROM "{node_table}"').fetchone()[0]) if node_table else None
    finally:
        connection.close()

    event_closures = []
    if args.events and args.events.is_file():
        for line in args.events.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("loop_closure_id", 0) > 0:
                event_closures.append({
                    "timestamp": event["timestamp"],
                    "ref_id": event["ref_id"],
                    "loop_closure_id": event["loop_closure_id"],
                })

    def unique_constraints(selected: list[dict]) -> list[dict]:
        unique = {}
        for link in selected:
            key = (min(link["from_id"], link["to_id"]), max(link["from_id"], link["to_id"]), link["type"])
            unique[key] = {
                "from_id": key[0],
                "to_id": key[1],
                "type": key[2],
                "type_name": link["type_name"],
                "node_id_gap": key[1] - key[0],
            }
        return list(unique.values())

    global_links = unique_constraints([link for link in links if link["type"] == 1])
    proximity_links = unique_constraints([link for link in links if link["type"] in (2, 3)])
    long_range_global_links = [link for link in global_links if link["node_id_gap"] >= 30]
    summary = {
        "database": str(args.database),
        "node_count": node_count,
        "directed_link_row_count": len(links),
        "directed_link_type_counts": {
            name: sum(link["type"] == value for link in links)
            for value, name in LINK_TYPES.items()
        },
        "unique_global_loop_closure_count": len(global_links),
        "long_range_global_loop_closure_count": len(long_range_global_links),
        "global_loop_closure_sample": (global_links[:10] + global_links[-10:]) if len(global_links) > 20 else global_links,
        "long_range_global_loop_closures": long_range_global_links,
        "unique_proximity_closure_count": len(proximity_links),
        "runtime_global_loop_event_count": len(event_closures),
        "runtime_global_loop_event_sample": (event_closures[:10] + event_closures[-10:]) if len(event_closures) > 20 else event_closures,
        "loop_closure_demonstrated": bool(global_links or event_closures),
        "criterion": "true only when RTAB-Map runtime Info reports a global loop or the database has a type=1 kGlobalClosure constraint",
    }
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
