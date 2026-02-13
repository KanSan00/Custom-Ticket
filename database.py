"""
データベース管理モジュール (SQLite)
チケットの作成・検索・更新を管理する。
Bot再起動時にデータが失われないよう、SQLiteファイルに永続化する。
"""

import sqlite3
from datetime import datetime
from typing import Optional

# データベースファイルパス
DB_PATH = "tickets.db"


def get_connection() -> sqlite3.Connection:
    """データベース接続を取得する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書風アクセスを有効化
    return conn


def init_db() -> None:
    """
    データベースを初期化する。
    tickets テーブルが存在しない場合に作成する。
    Bot起動時 (on_ready) に呼び出す。
    """
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                username    TEXT    NOT NULL DEFAULT '',
                channel_id  INTEGER NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'open',
                category    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                closed_at   TEXT
            )
        """)
        # 既存テーブルにusernameカラムがない場合に追加（マイグレーション）
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN username TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合は無視
        conn.commit()
    finally:
        conn.close()


def create_ticket(user_id: int, username: str, channel_id: int, category: str) -> int:
    """
    新しいチケットレコードを作成する。

    Args:
        user_id:    チケットを開いたユーザーのDiscord ID
        username:   ユーザー名
        channel_id: 作成されたチャンネルのID
        category:   カテゴリ (report / collab / question)

    Returns:
        作成されたチケットのID
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO tickets (user_id, username, channel_id, status, category, created_at)
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            (user_id, username, channel_id, category, datetime.now().isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_open_ticket(user_id: int) -> Optional[sqlite3.Row]:
    """
    指定ユーザーの未解決（open）チケットを取得する。
    重複チェックに使用。

    Args:
        user_id: チェックするユーザーのDiscord ID

    Returns:
        未解決チケットのRow、または None
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE user_id = ? AND status = 'open'",
            (user_id,),
        ).fetchone()
        return row
    finally:
        conn.close()


def close_ticket(channel_id: int) -> None:
    """
    チケットのステータスを 'closed' に更新する。

    Args:
        channel_id: 閉じるチケットチャンネルのID
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE tickets SET status = 'closed', closed_at = ?
            WHERE channel_id = ? AND status = 'open'
            """,
            (datetime.now().isoformat(), channel_id),
        )
        conn.commit()
    finally:
        conn.close()
