"""
チケット内操作 View
チケットチャンネル内に表示される「閉じる」ボタンと確認フローを管理する。

※ TicketCloseView は Persistent View (timeout=None) として実装。
  Bot再起動後もボタンが反応するよう、on_ready で bot.add_view() する必要がある。
"""

import io
from datetime import datetime

import discord
from discord.ui import View, Button, button

import config
import database


class TicketCloseView(View):
    """
    チケットチャンネル内に表示される「🔒 チケットを閉じる」ボタン。
    永続View (timeout=None) として動作する。
    """

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="チケットを閉じる",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, btn: Button
    ):
        """
        「チケットを閉じる」ボタンが押された際の処理。
        誤操作防止のため、確認フローを表示する。
        """
        embed = discord.Embed(
            title="⚠️ チケットを閉じますか？",
            description=(
                "この操作を実行すると、会話ログが保存された後、\n"
                "このチャンネルは**削除**されます。"
            ),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=TicketConfirmView(),
            ephemeral=True,
        )


class TicketConfirmView(View):
    """
    チケット削除の最終確認View。
    「はい、閉じます」「キャンセル」の2ボタン。
    """

    def __init__(self):
        super().__init__(timeout=60)  # 60秒でタイムアウト

    @button(
        label="はい、閉じます",
        emoji="✅",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_confirm_close",
    )
    async def confirm_close(
        self, interaction: discord.Interaction, btn: Button
    ):
        """
        確定ボタン。ログ保存 → DB更新 → チャンネル削除 を実行する。
        """
        channel = interaction.channel

        await interaction.response.send_message(
            "🔄 ログを保存してチケットを閉じています...", ephemeral=True
        )

        # --- 1. ログ保存 (Transcript生成) ---
        transcript = await self._generate_transcript(channel)

        # ログ保存チャンネルに送信
        log_channel = interaction.guild.get_channel(config.LOG_CHANNEL_ID)
        if log_channel:
            # チケット情報を取得してEmbedに表示
            embed = discord.Embed(
                title="📋 チケットログ",
                description=(
                    f"**チャンネル:** #{channel.name}\n"
                    f"**閉じた人:** {interaction.user.mention}\n"
                    f"**日時:** {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                ),
                color=discord.Color.greyple(),
            )

            # テキストファイルとして送信
            file = discord.File(
                io.BytesIO(transcript.encode("utf-8")),
                filename=f"transcript-{channel.name}.txt",
            )
            await log_channel.send(embed=embed, file=file)

        # --- 2. DB更新 ---
        database.close_ticket(channel.id)

        # --- 3. チャンネル削除 ---
        try:
            await channel.delete(reason="チケット解決済み")
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ チャンネルの削除権限がありません。管理者に連絡してください。",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ チャンネル削除中にエラーが発生しました: {e}",
                ephemeral=True,
            )

    @button(
        label="キャンセル",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_confirm_cancel",
    )
    async def cancel_close(
        self, interaction: discord.Interaction, btn: Button
    ):
        """キャンセルボタン。メッセージを削除して何もしない。"""
        await interaction.response.send_message(
            "✅ キャンセルしました。チケットは引き続きご利用いただけます。",
            ephemeral=True,
        )

    async def _generate_transcript(self, channel: discord.TextChannel) -> str:
        """
        チャンネル内の全メッセージを取得し、テキスト形式のトランスクリプトを生成する。

        Args:
            channel: 対象のテキストチャンネル

        Returns:
            トランスクリプトの文字列
        """
        lines = []
        lines.append(f"=== チケットログ: #{channel.name} ===")
        lines.append(f"生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
        lines.append("=" * 50)
        lines.append("")

        # メッセージを古い順に取得
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y/%m/%d %H:%M:%S")
            author = message.author.display_name
            content = message.content or "(メッセージ内容なし)"

            lines.append(f"[{timestamp}] {author}")
            lines.append(content)

            # 添付ファイルがある場合はURLを記載
            if message.attachments:
                for attachment in message.attachments:
                    lines.append(f"  📎 添付: {attachment.url}")

            # Embedがある場合はタイトルを記載
            if message.embeds:
                for embed in message.embeds:
                    if embed.title:
                        lines.append(f"  📋 Embed: {embed.title}")

            lines.append("")

        lines.append("=" * 50)
        lines.append("=== ログ終了 ===")

        return "\n".join(lines)
