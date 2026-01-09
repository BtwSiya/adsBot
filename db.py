import sqlite3

conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  approved INTEGER DEFAULT 0,
  message TEXT DEFAULT '',
  delay INTEGER DEFAULT 5,
  running INTEGER DEFAULT 0,
  sent_count INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner INTEGER,
  phone TEXT,
  session TEXT
)
""")

conn.commit()
