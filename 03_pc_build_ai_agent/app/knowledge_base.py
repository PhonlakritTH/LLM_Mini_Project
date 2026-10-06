"""SQLite-backed component knowledge seeded from the versioned JSON dataset."""
import json
import sqlite3
from pathlib import Path

from .config import settings

MODULE_ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = MODULE_ROOT / "data" / "components.json"


def load_components() -> list[dict]:
    seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    database_path = Path(settings.knowledge_database_path)
    if not database_path.is_absolute():
        database_path = MODULE_ROOT / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS components (
                part_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                rank INTEGER NOT NULL,
                specs_json TEXT NOT NULL,
                search_terms_json TEXT NOT NULL,
                source TEXT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS components_by_type ON components(type)")
        connection.executemany("""
            INSERT INTO components
                (part_id, type, name, brand, rank, specs_json, search_terms_json, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(part_id) DO UPDATE SET
                type=excluded.type, name=excluded.name, brand=excluded.brand, rank=excluded.rank,
                specs_json=excluded.specs_json, search_terms_json=excluded.search_terms_json,
                source=excluded.source
        """, [
            (part["part_id"], part["type"], part["name"], part["brand"], part["rank"],
             json.dumps(part["specs"], separators=(",", ":")),
             json.dumps(part["search_terms"], separators=(",", ":")), part["source"])
            for part in seed
        ])
        rows = connection.execute("""
            SELECT part_id, type, name, brand, rank, specs_json, search_terms_json, source
            FROM components ORDER BY type, part_id
        """).fetchall()

    return [{
        "part_id": row[0], "type": row[1], "name": row[2], "brand": row[3],
        "rank": row[4], "specs": json.loads(row[5]), "search_terms": json.loads(row[6]),
        "source": row[7],
    } for row in rows]


COMPONENTS = load_components()
BY_ID = {part["part_id"]: part for part in COMPONENTS}
BY_TYPE = {
    kind: [part for part in COMPONENTS if part["type"] == kind]
    for kind in {part["type"] for part in COMPONENTS}
}
