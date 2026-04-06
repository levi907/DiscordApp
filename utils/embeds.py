"""
Discord embed builders for consistent, styled message formatting.
"""
import discord
from data.models import Character, CampaignState, Quest
from data.campaign.spells import get_spell

# Color palette
COLOR_NARRATION   = 0x2C3E50   # dark blue-gray
COLOR_COMBAT      = 0xC0392B   # blood red
COLOR_SUCCESS     = 0x27AE60   # green
COLOR_WARNING     = 0xE67E22   # orange
COLOR_ERROR       = 0xE74C3C   # bright red
COLOR_INFO        = 0x3498DB   # blue
COLOR_GOLD        = 0xF39C12   # gold
COLOR_PURPLE      = 0x9B59B6   # purple (magic)


def narration_embed(text: str, title: str = "", location: str = "") -> discord.Embed:
    embed = discord.Embed(description=f"*{text}*", color=COLOR_NARRATION)
    if title:
        embed.title = title
    if location:
        embed.set_footer(text=f"📍 {location}")
    return embed


def combat_embed(title: str, description: str, footer: str = "") -> discord.Embed:
    embed = discord.Embed(title=f"⚔️ {title}", description=description, color=COLOR_COMBAT)
    if footer:
        embed.set_footer(text=footer)
    return embed


def character_sheet_embed(char: Character) -> discord.Embed:
    """Full character sheet styled after a physical D&D stat block."""
    ab   = char.ability_scores
    prof = char.proficiency_bonus

    # Embed colour tracks HP
    pct = char.current_hp / char.max_hp if char.max_hp > 0 else 0
    color = (
        0x2ECC71   if pct >  0.5 else   # healthy green
        COLOR_WARNING if pct > 0.25 else  # wounded orange
        COLOR_ERROR   if pct >  0    else  # critical red
        0x34495E                           # dead slate
    )

    status_icon = "💀" if char.current_hp == 0 else "⚔️"
    embed = discord.Embed(color=color)
    embed.title = f"{status_icon}  {char.name}"
    embed.description = f"*{char.race}  ·  {char.char_class}  ·  Level {char.level}*"

    # ── Row 1: Initiative | HP (centre) | Speed ─────────────────────────
    init     = ab.dex_mod
    init_str = f"+{init}" if init >= 0 else str(init)
    hp_bar   = _hp_bar(char.current_hp, char.max_hp, length=12)
    hp_temp  = f"  (+{char.temp_hp} tmp)" if char.temp_hp else ""

    embed.add_field(name="Initiative",    value=f"**{init_str}**",                              inline=True)
    embed.add_field(name="❤️  HP",        value=f"**{char.current_hp}** / {char.max_hp}{hp_temp}\n{hp_bar}", inline=True)
    embed.add_field(name="Speed",         value=f"**{char.speed} ft**",                         inline=True)

    # ── Row 2: Hit Dice | Armor Class | Proficiency ──────────────────────
    embed.add_field(name="Hit Dice",      value=f"**{char.hit_dice}**",         inline=True)
    embed.add_field(name="Armor Class",   value=f"**{char.armor_class}**",      inline=True)
    embed.add_field(name="Proficiency",   value=f"**+{prof}**",                 inline=True)

    # ── Ability Score table (2-column, Score / Mod / Save per stat) ──────
    profs_lower = {s.lower() for s in char.saving_throw_proficiencies}

    def _m(v: int) -> str:
        return f"+{v}" if v >= 0 else str(v)

    def _s(key: str, mod: int) -> str:
        bonus = prof if key in profs_lower else 0
        t = mod + bonus
        return f"+{t}" if t >= 0 else str(t)

    pairs = [
        ("STR", ab.strength,     ab.str_mod, "strength",
         "INT", ab.intelligence, ab.int_mod, "intelligence"),
        ("DEX", ab.dexterity,    ab.dex_mod, "dexterity",
         "WIS", ab.wisdom,       ab.wis_mod, "wisdom"),
        ("CON", ab.constitution, ab.con_mod, "constitution",
         "CHA", ab.charisma,     ab.cha_mod, "charisma"),
    ]

    col_hdr  = "     Sc   Mod  Save"         # 19 chars — aligns with data rows
    divider  = "─" * 19 + "─┼─" + "─" * 19
    tbl_rows = [col_hdr + "  │  " + col_hdr, divider]

    for n1, s1, m1, k1, n2, s2, m2, k2 in pairs:
        left  = f"{n1}  {s1:2}  {_m(m1):>3}  {_s(k1,m1):>4}"
        right = f"{n2}  {s2:2}  {_m(m2):>3}  {_s(k2,m2):>4}"
        tbl_rows.append(f"{left}  │  {right}")

    table = "```\n" + "\n".join(tbl_rows) + "\n```"
    embed.add_field(name="📊  Ability Scores", value=table, inline=False)

    # ── Conditions / Death Saves ─────────────────────────────────────────
    if char.conditions:
        embed.add_field(name="⚠️ Conditions", value=", ".join(char.conditions), inline=False)

    if char.current_hp == 0:
        ds = char.death_saves
        embed.add_field(
            name="💀 Death Saves",
            value=f"✅ {ds['successes']} / 3   ❌ {ds['failures']} / 3",
            inline=False,
        )

    embed.set_footer(text=f"XP: {char.experience_points}  ·  Gold: {char.gold} gp  ·  {', '.join(char.languages or ['Common'])}")
    return embed


def spells_embed(char: Character) -> discord.Embed:
    """Spell list and slot tracker embed."""
    embed = discord.Embed(
        title=f"✨ {char.name}'s Spells",
        color=COLOR_PURPLE,
    )

    # Spell slots
    if char.spell_slots.slots:
        slot_lines = []
        for level in sorted(char.spell_slots.slots.keys()):
            avail = char.spell_slots.available(level)
            total = char.spell_slots.slots[level]
            dots = "●" * avail + "○" * (total - avail)
            slot_lines.append(f"Level {level}: {dots} ({avail}/{total})")
        embed.add_field(name="Spell Slots", value="\n".join(slot_lines), inline=False)
        embed.add_field(name="Spell Attack", value=f"+{char.spell_attack_bonus()}", inline=True)
        embed.add_field(name="Save DC", value=str(char.spell_save_dc()), inline=True)

    if char.cantrips:
        embed.add_field(name="Cantrips (∞)", value="\n".join(char.cantrips), inline=False)

    prepared = char.prepared_spells or char.known_spells
    if prepared:
        by_level: dict[int, list[str]] = {}
        for spell_name in prepared:
            s = get_spell(spell_name)
            lvl = s["level"] if s else 1
            by_level.setdefault(lvl, []).append(spell_name)

        for lvl in sorted(by_level.keys()):
            if lvl == 0:
                continue
            avail = char.spell_slots.available(lvl)
            embed.add_field(
                name=f"Level {lvl} Spells (slots: {avail})",
                value="\n".join(by_level[lvl]),
                inline=False,
            )

    return embed


def inventory_embed(char: Character) -> discord.Embed:
    """Inventory embed."""
    embed = discord.Embed(title=f"🎒 {char.name}'s Inventory", color=COLOR_GOLD)
    embed.add_field(name="Gold", value=f"{char.gold} gp", inline=True)

    weapons = [i for i in char.inventory if i.item_type == "weapon"]
    armor   = [i for i in char.inventory if i.item_type == "armor"]
    consumables = [i for i in char.inventory if i.item_type == "consumable"]
    misc    = [i for i in char.inventory if i.item_type == "misc"]

    def fmt_items(items):
        lines = []
        for item in items:
            equipped = " ⚔️" if item.equipped else ""
            qty = f" ×{item.quantity}" if item.quantity > 1 else ""
            dmg = f" `{item.damage}`" if item.damage else ""
            lines.append(f"• **{item.name}**{qty}{equipped}{dmg}")
        return "\n".join(lines) or "*empty*"

    if weapons:
        embed.add_field(name="Weapons", value=fmt_items(weapons), inline=False)
    if armor:
        embed.add_field(name="Armor", value=fmt_items(armor), inline=False)
    if consumables:
        embed.add_field(name="Consumables", value=fmt_items(consumables), inline=False)
    if misc:
        embed.add_field(name="Miscellaneous", value=fmt_items(misc), inline=False)

    return embed


def quest_embed(quest: Quest) -> discord.Embed:
    color = COLOR_SUCCESS if quest.status == "completed" else (
        COLOR_ERROR if quest.status == "failed" else COLOR_GOLD
    )
    status_icon = {"active": "📌", "completed": "✅", "failed": "❌"}.get(quest.status, "📌")

    embed = discord.Embed(
        title=f"{status_icon} {quest.title}",
        description=quest.description,
        color=color,
    )
    if quest.giver:
        embed.add_field(name="Quest Giver", value=quest.giver, inline=True)
    if quest.location:
        embed.add_field(name="Location", value=quest.location, inline=True)

    if quest.objectives:
        obj_lines = []
        for obj in quest.objectives:
            check = "✅" if obj.get("completed") else "◻️"
            obj_lines.append(f"{check} {obj['text']}")
        embed.add_field(name="Objectives", value="\n".join(obj_lines), inline=False)

    if quest.rewards:
        rewards = quest.rewards
        reward_text = rewards.get("description", "")
        if rewards.get("gold"):
            reward_text += f"\n💰 {rewards['gold']} gp"
        if reward_text:
            embed.add_field(name="Rewards", value=reward_text.strip(), inline=False)

    return embed


def campaign_status_embed(campaign: CampaignState, player_count: int) -> discord.Embed:
    from data.campaign.lmop import CHAPTERS
    chapter_data = CHAPTERS.get(campaign.chapter, {})

    embed = discord.Embed(
        title=f"🗺️ {campaign.campaign_name}",
        description=f"*{chapter_data.get('summary', '')}*",
        color=COLOR_INFO,
    )
    embed.add_field(name="Chapter", value=f"{campaign.chapter}: {chapter_data.get('title', '')}", inline=True)
    embed.add_field(name="Location", value=campaign.current_location, inline=True)
    embed.add_field(name="Session", value=str(campaign.session_number), inline=True)
    embed.add_field(name="Players", value=str(player_count), inline=True)

    if campaign.important_npcs:
        npc_text = "\n".join(f"• **{name}**: {desc}" for name, desc in list(campaign.important_npcs.items())[:5])
        embed.add_field(name="Known NPCs", value=npc_text, inline=False)

    if campaign.discovered_locations:
        embed.add_field(name="Discovered Locations", value=", ".join(campaign.discovered_locations[:8]), inline=False)

    return embed


def combat_status_embed(combat_status_text: str, round_number: int, current_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚔️ Combat — Round {round_number}",
        description=combat_status_text,
        color=COLOR_COMBAT,
    )
    embed.set_footer(text=f"Current turn: {current_name}")
    return embed


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(description=f"❌ {message}", color=COLOR_ERROR)


def success_embed(message: str) -> discord.Embed:
    return discord.Embed(description=f"✅ {message}", color=COLOR_SUCCESS)


def info_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=COLOR_INFO)


def _hp_bar(current: int, maximum: int, length: int = 10) -> str:
    if maximum == 0:
        return "░" * length
    filled = round((current / maximum) * length)
    filled = max(0, min(filled, length))
    bar = "█" * filled + "░" * (length - filled)
    return f"`[{bar}]`"
