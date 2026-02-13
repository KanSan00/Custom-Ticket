"""
設定管理モジュール
.env ファイルから環境変数を読み込み、Botの設定値として公開する。
"""

import os
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# --- Bot設定 ---
# Discord Botトークン
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# 運営ロールID（チケットチャンネルの閲覧権限を付与するロール）
ADMIN_ROLE_ID: int = int(os.getenv("ADMIN_ROLE_ID", "0"))

# チケットチャンネルを作成するカテゴリのID
TICKET_CATEGORY_ID: int = int(os.getenv("TICKET_CATEGORY_ID", "0"))

# ログ保存先チャンネルID（チケット閉鎖時にトランスクリプトを送信）
LOG_CHANNEL_ID: int = int(os.getenv("LOG_CHANNEL_ID", "0"))
