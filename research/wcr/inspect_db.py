import json
import duckdb
from pathlib import Path

DB = Path("ashare_pit.duckdb")
con = duckdb.connect(str(DB), read_only=True)

tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
out = {"tables": []}

for t in tables:
    cols = con.execute(f"PRAGMA table_info('{t}')").fetchall()
    col_names = [c[1] for c in cols]
    sample = []
    try:
        rows = con.execute(f'SELECT * FROM "{t}" LIMIT 3').fetchall()
        sample = [dict(zip(col_names, row)) for row in rows]
    except Exception as e:
        sample = [{"error": str(e)}]
    count = None
    try:
        count = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except Exception:
        pass
    out["tables"].append({
        "name": t,
        "count": count,
        "columns": [
            {"cid": c[0], "name": c[1], "type": c[2], "notnull": bool(c[3]), "default": c[4], "pk": bool(c[5])}
            for c in cols
        ],
        "sample": sample,
    })

Path("wcr_artifacts").mkdir(exist_ok=True)
Path("wcr_artifacts/schema.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)
print(json.dumps({"table_count": len(tables), "tables": tables}, ensure_ascii=False))
