"""
Discord channel and permission utilities for the D&D bot.
"""
import discord
from typing import Optional


async def _resolve_members(guild: discord.Guild, player_ids: list[str]) -> list[discord.Member]:
    """Fetch members by ID, using cache where possible."""
    members = []
    for pid in player_ids:
        member = guild.get_member(int(pid))
        if member is None:
            try:
                member = await guild.fetch_member(int(pid))
            except discord.HTTPException:
                pass
        if member:
            members.append(member)
    return members


async def create_campaign_category(
    guild: discord.Guild, campaign_name: str
) -> discord.CategoryChannel:
    """Create a category for all campaign channels."""
    return await guild.create_category(
        name=f"⚔️ {campaign_name}",
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        },
    )


async def create_narration_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    player_ids: list[str],
    bot_member,
) -> discord.TextChannel:
    """
    Create the main narration channel.
    Visible to all players (read-only) + bot.
    """
    overwrites: dict = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_messages=True, embed_links=True
        ),
    }
    for member in await _resolve_members(guild, player_ids):
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=False, read_message_history=True
        )

    return await guild.create_text_channel(
        name="📖narration",
        category=category,
        topic="The DM's narration channel. Read-only for players.",
        overwrites=overwrites,
    )


async def create_log_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    player_ids: list[str],
    bot_member,
) -> discord.TextChannel:
    """
    Create the game log channel (quests, summaries, combat logs).
    Visible to all players (read-only) + bot.
    """
    overwrites: dict = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_messages=True, embed_links=True
        ),
    }
    for member in await _resolve_members(guild, player_ids):
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True, send_messages=False, read_message_history=True
        )

    return await guild.create_text_channel(
        name="📋game-log",
        category=category,
        topic="Quests, combat logs, session summaries, and loot.",
        overwrites=overwrites,
    )


async def create_player_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    player: discord.Member,
    bot_member,
) -> discord.TextChannel:
    """
    Create a private channel for one player.
    Only visible to that player and the bot.
    """
    overwrites: dict = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_messages=True, embed_links=True
        ),
        player: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True, embed_links=True
        ),
    }

    safe_name = player.display_name.lower().replace(" ", "-")[:20]
    return await guild.create_text_channel(
        name=f"🧙{safe_name}",
        category=category,
        topic=f"Private channel for {player.display_name}. Character management, actions, and private info.",
        overwrites=overwrites,
    )


async def cleanup_campaign_channels(
    guild: discord.Guild,
    campaign_category_id: str,
):
    """Delete all channels in the campaign category and the category itself."""
    category = guild.get_channel(int(campaign_category_id))
    if not category or not isinstance(category, discord.CategoryChannel):
        return

    for channel in category.channels:
        try:
            await channel.delete(reason="Campaign ended")
        except discord.HTTPException:
            pass

    try:
        await category.delete(reason="Campaign ended")
    except discord.HTTPException:
        pass


async def add_player_to_channels(
    guild: discord.Guild,
    player: discord.Member,
    narration_channel_id: str,
    log_channel_id: str,
):
    """Grant an existing player access to narration and log channels."""
    for cid in [narration_channel_id, log_channel_id]:
        channel = guild.get_channel(int(cid))
        if channel:
            await channel.set_permissions(
                player,
                view_channel=True, send_messages=False, read_message_history=True
            )
