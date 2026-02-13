"""
チケット開設パネル View
サーバーに常設表示されるEmbed + ボタンのView。
ユーザーがボタンを押すとプライベートチケットチャンネルが作成される。

※ Persistent View (timeout=None) として実装。
  Bot再起動後もボタンが反応するよう、on_ready で bot.add_view() する必要がある。
"""

import discord
from discord.ui import View, Button

import config
import database
from views.ticket_view import TicketCloseView

# カテゴリ定義: (custom_id, ラベル, 絵文字, ボタンスタイル, チャンネル名略称)
CATEGORIES = [
    ("ticket_report", "通報・違反報告", "🚨", discord.ButtonStyle.danger, "rep"),
    ("ticket_collab", "コラボ・企画提案", "🤝", discord.ButtonStyle.success, "collab"),
    ("ticket_question", "その他の質問", "❓", discord.ButtonStyle.secondary, "question"),
]


class TicketPanelView(View):
    """
    チケット開設パネルのView（永続）。
    3つのカテゴリボタンを持ち、押下時にプライベートチャンネルを生成する。
    """

    def __init__(self):
        super().__init__(timeout=None)

        # カテゴリ定義からボタンを動的に生成
        for custom_id, label, emoji, style, short_name in CATEGORIES:
            button = Button(
                label=label,
                emoji=emoji,
                style=style,
                custom_id=custom_id,
            )
            # コールバックをバインド（short_nameをクロージャでキャプチャ）
            button.callback = self._make_callback(short_name)
            self.add_item(button)

    def _make_callback(self, category_short: str):
        """
        各ボタンのコールバック関数を生成する。
        クロージャを使ってカテゴリ名をキャプチャする。
        """

        async def callback(interaction: discord.Interaction):
            await self._handle_ticket_creation(interaction, category_short)

        return callback

    async def _handle_ticket_creation(
        self, interaction: discord.Interaction, category: str
    ):
        """
        チケット作成のメインロジック。

        1. 重複チェック
        2. 権限設定の構築
        3. チャンネル作成
        4. DB登録
        5. 初期メッセージ送信
        """
        guild = interaction.guild
        user = interaction.user

        # --- 1. 重複チェック ---
        existing = database.get_open_ticket(user.id)
        if existing:
            # チャンネルが実際に存在するか確認（手動削除対策）
            existing_channel = guild.get_channel(existing["channel_id"])
            if existing_channel is None:
                # チャンネルが存在しない → DBをクリーンアップして続行
                database.close_ticket(existing["channel_id"])
            else:
                # チャンネルが存在する → 重複として拒否
                await interaction.response.send_message(
                    f"⚠️ すでにチケットが開かれています: {existing_channel.mention}\n"
                    f"既存のチケットをご利用ください。",
                    ephemeral=True,
                )
                return

        # --- 2. カテゴリ（親チャンネル）の取得 ---
        ticket_category = guild.get_channel(config.TICKET_CATEGORY_ID)
        if ticket_category is None:
            await interaction.response.send_message(
                "❌ チケットカテゴリが見つかりません。管理者に連絡してください。",
                ephemeral=True,
            )
            return

        # --- 3. 権限設定 (Permission Overwrites) ---
        admin_role = guild.get_role(config.ADMIN_ROLE_ID)
        overwrites = {
            # @everyone → 閲覧不可
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            # Bot自身 → 閲覧・送信可（必須：Botがチャンネルにメッセージを送るため）
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True
            ),
            # 実行ユーザー → 閲覧・送信可
            user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            ),
        }
        # 運営ロールが存在する場合のみ追加
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )

        # --- 4. チャンネル作成 ---
        # ユーザー名からDiscordのチャンネル名に使えない文字を除去
        safe_name = user.name.replace(" ", "-").lower()
        channel_name = f"ticket-{category}-{safe_name}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=ticket_category,
                overwrites=overwrites,
                reason=f"チケット作成: {user.name} ({category})",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ チャンネルの作成権限がありません。Botの権限を確認してください。",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ チャンネル作成中にエラーが発生しました: {e}",
                ephemeral=True,
            )
            return

        # --- 5. DB登録 ---
        ticket_id = database.create_ticket(user.id, user.name, ticket_channel.id, category)

        # --- 6. ユーザーへの応答 (Ephemeral) ---
        await interaction.response.send_message(
            f"✅ チケットを作成しました: {ticket_channel.mention}",
            ephemeral=True,
        )

        # --- 7. チケットチャンネルに初期メッセージを投稿 ---
        # カテゴリの日本語名を取得
        category_names = {
            "rep": "🚨 通報・違反報告",
            "collab": "🤝 コラボ・企画提案",
            "question": "❓ その他の質問",
        }
        cat_display = category_names.get(category, category)

        embed = discord.Embed(
            title="📩 チケットが作成されました",
            description=(
                f"{user.mention} さん、お問い合わせありがとうございます。\n\n"
                f"**カテゴリ:** {cat_display}\n"
                f"**チケットID:** #{ticket_id}\n\n"
                "担当者が来るまで、詳細をご記入ください。\n"
                "解決しましたら、下のボタンでチケットを閉じてください。"
            ),
            color=discord.Color.blue(),
        )

        await ticket_channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=TicketCloseView(),
        )
