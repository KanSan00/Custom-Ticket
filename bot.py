"""
お問い合わせチケットBot (Custom Ticket)
=========================================

サーバー管理者への連絡窓口を一元化するDiscord Bot。
ユーザーがボタンを押すことで、プライベートなチケットチャンネルを自動作成する。

使い方:
    1. .env.example を .env にコピーし、各値を設定
    2. pip install -r requirements.txt
    3. python bot.py
    4. Discord上で /setup_ticket を実行してパネルを設置
"""

import discord
from discord import app_commands
from discord.ext import commands

import config
import database
from views.panel_view import TicketPanelView
from views.ticket_view import TicketCloseView


# --- Bot初期化 ---
# 必要な Intents を設定
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --- イベントハンドラ ---
@bot.event
async def on_ready():
    """
    Bot起動時の処理。
    - データベースの初期化
    - Persistent View (永続ボタン) の再登録
    - スラッシュコマンドの同期
    """
    # データベース初期化
    database.init_db()
    print(f"✅ データベースを初期化しました")

    # 永続Viewの登録（Bot再起動後もボタンが反応するようにする）
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    print(f"✅ 永続Viewを登録しました")

    # スラッシュコマンドを同期
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} 個のコマンドを同期しました")
    except Exception as e:
        print(f"❌ コマンド同期エラー: {e}")

    print(f"🤖 {bot.user.name} が起動しました！ (ID: {bot.user.id})")
    print(f"📊 {len(bot.guilds)} サーバーに接続中")


# --- スラッシュコマンド ---
@bot.tree.command(
    name="setup_ticket",
    description="お問い合わせチケットパネルをこのチャンネルに設置します",
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_ticket(interaction: discord.Interaction):
    """
    /setup_ticket コマンド。
    管理者のみが実行可能。実行したチャンネルにチケット開設パネルを設置する。
    """
    # パネル用の Embed を作成
    embed = discord.Embed(
        title="📬 お問い合わせ窓口",
        description=(
            "御用の方は以下のボタンからカテゴリを選択してください。\n"
            "運営との専用チャンネルが作成されます。\n\n"
            "**🚨 通報・違反報告**\n"
            "ルール違反やトラブルの報告\n\n"
            "**🤝 コラボ・企画提案**\n"
            "コラボレーションや企画の相談\n\n"
            "**❓ その他の質問**\n"
            "上記以外のお問い合わせ"
        ),
        color=discord.Color.gold(),
    )
    embed.set_footer(text="※ お一人様につき同時に1つのチケットのみ作成できます。")

    # パネルを送信
    await interaction.channel.send(embed=embed, view=TicketPanelView())

    # 実行者への確認メッセージ (Ephemeral)
    await interaction.response.send_message(
        "✅ チケットパネルを設置しました！", ephemeral=True
    )


# コマンドエラーハンドラ
@setup_ticket.error
async def setup_ticket_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """権限不足時のエラーハンドリング。"""
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ このコマンドは管理者のみ実行できます。", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ エラーが発生しました: {error}", ephemeral=True
        )


# --- Bot起動 ---
if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("❌ エラー: DISCORD_TOKEN が設定されていません。")
        print("   .env.example を .env にコピーし、Botトークンを設定してください。")
    else:
        print("🚀 Botを起動しています...")
        bot.run(config.DISCORD_TOKEN)
