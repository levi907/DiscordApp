"""
Async SQLite database layer for the D&D bot.
"""
from __future__ import annotations
import json
import aiosqlite
from typing import Optional
from config import DATABASE_PATH
from data.models import Character, CampaignState, CombatState


CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS characters (
    discord_id TEXT NOT NULL,
    guild_id   TEXT NOT NULL,
    data       TEXT NOT NULL,
    PRIMARY KEY (discord_id, guild_id)
);

CREATE TABLE IF NOT EXISTS campaigns (
    guild_id TEXT PRIMARY KEY,
    data     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS combat_states (
    guild_id     TEXT PRIMARY KEY,
    encounter_id TEXT NOT NULL,
    data         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  TEXT NOT NULL,
    log_type  TEXT NOT NULL,
    content   TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(CREATE_TABLES)
        await db.commit()


# ---------------------------------------------------------------------------
# Character operations
# ---------------------------------------------------------------------------

async def save_character(character: Character, guild_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO characters (discord_id, guild_id, data) VALUES (?, ?, ?)",
            (character.discord_id, guild_id, json.dumps(character.to_dict()))
        )
        await db.commit()


async def load_character(discord_id: str, guild_id: str) -> Optional[Character]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT data FROM characters WHERE discord_id=? AND guild_id=?",
            (discord_id, guild_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return Character.from_dict(json.loads(row[0]))
    return None


async def load_all_characters(guild_id: str) -> list[Character]:
    chars = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT data FROM characters WHERE guild_id=?", (guild_id,)
        ) as cursor:
            async for row in cursor:
                chars.append(Character.from_dict(json.loads(row[0])))
    return chars


async def delete_character(discord_id: str, guild_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM characters WHERE discord_id=? AND guild_id=?",
            (discord_id, guild_id)
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Campaign operations
# ---------------------------------------------------------------------------

async def save_campaign(campaign: CampaignState):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO campaigns (guild_id, data) VALUES (?, ?)",
            (campaign.guild_id, json.dumps(campaign.to_dict()))
        )
        await db.commit()


async def load_campaign(guild_id: str) -> Optional[CampaignState]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT data FROM campaigns WHERE guild_id=?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return CampaignState.from_dict(json.loads(row[0]))
    return None


async def delete_campaign(guild_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM campaigns WHERE guild_id=?", (guild_id,))
        await db.execute("DELETE FROM characters WHERE guild_id=?", (guild_id,))
        await db.execute("DELETE FROM combat_states WHERE guild_id=?", (guild_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Combat state operations
# ---------------------------------------------------------------------------

async def save_combat(guild_id: str, combat: CombatState):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO combat_states (guild_id, encounter_id, data) VALUES (?, ?, ?)",
            (guild_id, combat.encounter_id, json.dumps(combat.to_dict()))
        )
        await db.commit()


async def load_combat(guild_id: str) -> Optional[CombatState]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT data FROM combat_states WHERE guild_id=?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return CombatState.from_dict(json.loads(row[0]))
    return None


async def delete_combat(guild_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM combat_states WHERE guild_id=?", (guild_id,))
        await db.commit()


# ---------------------------------------------------------------------------
# Game log operations
# ---------------------------------------------------------------------------

async def append_log(guild_id: str, log_type: str, content: str):
    """log_type: 'combat', 'quest', 'summary', 'loot'"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO game_logs (guild_id, log_type, content) VALUES (?, ?, ?)",
            (guild_id, log_type, content)
        )
        await db.commit()


async def get_logs(guild_id: str, log_type: Optional[str] = None, limit: int = 20) -> list[dict]:
    logs = []
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if log_type:
            query = "SELECT log_type, content, timestamp FROM game_logs WHERE guild_id=? AND log_type=? ORDER BY timestamp DESC LIMIT ?"
            params = (guild_id, log_type, limit)
        else:
            query = "SELECT log_type, content, timestamp FROM game_logs WHERE guild_id=? ORDER BY timestamp DESC LIMIT ?"
            params = (guild_id, limit)
        async with db.execute(query, params) as cursor:
            async for row in cursor:
                logs.append({"type": row[0], "content": row[1], "timestamp": row[2]})
    return logs
