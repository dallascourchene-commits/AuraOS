"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8ea-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: MIIGWECH (Extension-Based Storage)
DEPENDENCIES: pathlib, sqlite3
FUNCTIONS: None
SYNOPSIS: The module is a lightweight Python utility leveraging `pathlib` for filesystem operations and `sqlite3` for embedded database management, with no exposed functions.
[/AURA_MASTER_KEY]
"""
# [AURA OPTIMIZED] - Bloat removed.

import sqlite3
from pathlib import Path
db_path = Path.home() / ".mempalace" / "aura_memory.db"
conn = sqlite3.connect(db_path)
conn.execute('''
    CREATE TABLE IF NOT EXISTS arxiv_cursors (
        topic TEXT PRIMARY KEY,
        last_offset INTEGER
    )
''')
conn.commit()
conn.close()
print("[+] Table 'arxiv_cursors' created. Database is now stable.")
