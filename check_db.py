"""DBの中身を確認するユーティリティスクリプト"""
import sqlite3

conn = sqlite3.connect("tickets.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM tickets ORDER BY ticket_id").fetchall()

print(f"{'ID':<4} {'Username':<18} {'Status':<8} {'Category':<10} {'Created':<22} {'Closed'}")
print("-" * 90)
for r in rows:
    created = str(r["created_at"])[:19] if r["created_at"] else "-"
    closed = str(r["closed_at"])[:19] if r["closed_at"] else "-"
    username = r["username"] if "username" in r.keys() and r["username"] else "-"
    print(f"{r['ticket_id']:<4} {username:<18} {r['status']:<8} {r['category']:<10} {created:<22} {closed}")

print(f"\n合計: {len(rows)} 件")
conn.close()
