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
    """Full character sheet embed."""
    embed = discord.Embed(
        title=f"📜 {char.name}",
        description=f"*{char.race} {char.char_class} — Level {char.level}*\n{char.background} | {char.alignment}",
        color=COLOR_INFO,
    )

    # Ability scores
    ab = char.ability_scores
    def fmt(score, mod): return f"{score} ({'+' if mod >= 0 else ''}{mod})"
    embed.add_field(name="STR", value=fmt(ab.strength, ab.str_mod), inline=True)
    embed.add_field(name="DEX", value=fmt(ab.dexterity, ab.dex_mod), inline=True)
    embed.add_field(name="CON", value=fmt(ab.constitution, ab.con_mod), inline=True)
    embed.add_field(name="INT", value=fmt(ab.intelligence, ab.int_mod), inline=True)
    embed.add_field(name="WIS", value=fmt(ab.wisdom, ab.wis_mod), inline=True)
    embed.add_field(name="CHA", value=fmt(ab.charisma, ab.cha_mod), inline=True)

    # HP / AC
    hp_bar = _hp_bar(char.current_hp, char.max_hp)
    embed.add_field(
        name="Hit Points",
        value=f"{hp_bar}\n{char.current_hp}/{char.max_hp} HP" + (f" (+{char.temp_hp} temp)" if char.temp_hp else ""),
        inline=True,
    )
    embed.add_field(name="Armor Class", value=str(char.armor_class), inline=True)
    embed.add_field(name="Speed", value=f"{char.speed} ft", inline=True)
    embed.add_field(name="Prof. Bonus", value=f"+{char.proficiency_bonus}", inline=True)
    embed.add_field(name="Hit Dice", value=char.hit_dice, inline=True)
    embed.add_field(name="XP", value=str(char.experience_points), inline=True)

    # Conditions
    if char.conditions:
        embed.add_field(name="⚠️ Conditions", value=", ".join(char.conditions), inline=False)

    # Death saves
    if char.current_hp == 0:
        ds = char.death_saves
        embed.add_field(
            name="💀 Death Saves",
            value=f"✅ {ds['successes']}/3  ❌ {ds['failures']}/3",
            inline=False,
        )

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
