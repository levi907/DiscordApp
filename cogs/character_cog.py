"""
Character management cog.
Handles character creation, viewing stats, managing inventory,
resting, and character progression.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands

import data.database as db
from data.models import Character, AbilityScores, SpellSlots
from data.campaign.lmop import CLASS_ARCHETYPES, get_class_archetype
from data.campaign.items import starting_equipment, get_item
from engine.dice import roll_ability_scores
from engine.rules import (
    CLASS_HIT_DICE, proficiency_bonus, spell_slots_for_class, xp_for_level,
)
from utils.embeds import (
    character_sheet_embed, spells_embed, inventory_embed,
    error_embed, success_embed, info_embed,
)


VALID_RACES = [
    "Human", "Elf", "Dwarf", "Halfling", "Half-Elf",
    "Half-Orc", "Gnome", "Dragonborn", "Tiefling",
]

VALID_CLASSES = [
    "Fighter", "Wizard", "Rogue", "Cleric", "Ranger",
    "Paladin", "Barbarian", "Bard", "Warlock", "Sorcerer", "Druid", "Monk",
]

# Racial ability score bonuses
RACIAL_BONUSES: dict[str, dict[str, int]] = {
    "Human":      {"strength": 1, "dexterity": 1, "constitution": 1,
                   "intelligence": 1, "wisdom": 1, "charisma": 1},
    "Elf":        {"dexterity": 2, "intelligence": 1},
    "Dwarf":      {"constitution": 2, "wisdom": 1},
    "Halfling":   {"dexterity": 2, "charisma": 1},
    "Half-Elf":   {"charisma": 2},
    "Half-Orc":   {"strength": 2, "constitution": 1},
    "Gnome":      {"intelligence": 2, "dexterity": 1},
    "Dragonborn": {"strength": 2, "charisma": 1},
    "Tiefling":   {"intelligence": 1, "charisma": 2},
}

# Racial base speed
RACIAL_SPEED: dict[str, int] = {
    "Dwarf": 25, "Halfling": 25, "Gnome": 25,
}


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _player_channel(self, campaign, discord_id: str, guild: discord.Guild):
        ch_id = campaign.player_channel_ids.get(discord_id)
        if not ch_id:
            return None
        return guild.get_channel(int(ch_id))

    def _is_in_player_channel(self, interaction: discord.Interaction, campaign) -> bool:
        """Check the interaction is from the player's private channel."""
        if not campaign:
            return False
        discord_id = str(interaction.user.id)
        ch_id = campaign.player_channel_ids.get(discord_id)
        return ch_id and str(interaction.channel_id) == ch_id

    # ------------------------------------------------------------------
    # /character create
    # ------------------------------------------------------------------

    @app_commands.command(name="character_create", description="Create your D&D character")
    @app_commands.describe(
        name="Your character's name",
        race="Your character's race",
        char_class="Your character's class",
    )
    async def character_create(
        self,
        interaction: discord.Interaction,
        name: str,
        race: str,
        char_class: str,
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        campaign = await db.load_campaign(guild_id)
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign. Ask the DM to start one."))
            return

        if discord_id not in campaign.player_ids:
            await interaction.followup.send(embed=error_embed("You are not a player in the current campaign."))
            return

        # Validate
        race = race.title()
        char_class = char_class.title()

        if race not in VALID_RACES:
            await interaction.followup.send(embed=error_embed(
                f"Invalid race. Choose from: {', '.join(VALID_RACES)}"
            ))
            return

        if char_class not in VALID_CLASSES:
            await interaction.followup.send(embed=error_embed(
                f"Invalid class. Choose from: {', '.join(VALID_CLASSES)}"
            ))
            return

        # Check if character exists
        existing = await db.load_character(discord_id, guild_id)
        if existing:
            await interaction.followup.send(embed=error_embed(
                f"You already have a character ({existing.name}). "
                "Contact the DM to reset your character."
            ))
            return

        # Roll ability scores
        scores = roll_ability_scores()
        scores.sort(reverse=True)

        # Get class archetype
        archetype = get_class_archetype(char_class) or {}
        racial_bonuses = RACIAL_BONUSES.get(race, {})

        # Assign scores to abilities (standard priority: STR, DEX, CON, INT, WIS, CHA)
        # Adjust for class
        class_priority: dict[str, list[str]] = {
            "Fighter":   ["strength", "constitution", "dexterity", "wisdom", "intelligence", "charisma"],
            "Wizard":    ["intelligence", "constitution", "dexterity", "wisdom", "strength", "charisma"],
            "Rogue":     ["dexterity", "intelligence", "constitution", "charisma", "wisdom", "strength"],
            "Cleric":    ["wisdom", "constitution", "strength", "charisma", "dexterity", "intelligence"],
            "Ranger":    ["dexterity", "wisdom", "constitution", "strength", "intelligence", "charisma"],
            "Paladin":   ["strength", "charisma", "constitution", "wisdom", "dexterity", "intelligence"],
            "Barbarian": ["strength", "constitution", "dexterity", "wisdom", "intelligence", "charisma"],
            "Bard":      ["charisma", "dexterity", "constitution", "intelligence", "wisdom", "strength"],
            "Warlock":   ["charisma", "constitution", "dexterity", "intelligence", "wisdom", "strength"],
            "Sorcerer":  ["charisma", "constitution", "dexterity", "intelligence", "wisdom", "strength"],
            "Druid":     ["wisdom", "constitution", "dexterity", "strength", "intelligence", "charisma"],
            "Monk":      ["dexterity", "wisdom", "constitution", "strength", "intelligence", "charisma"],
        }
        priority = class_priority.get(char_class, list(class_priority["Fighter"]))
        score_map = dict(zip(priority, scores))

        ability_scores = AbilityScores(
            strength=score_map.get("strength", 10) + racial_bonuses.get("strength", 0),
            dexterity=score_map.get("dexterity", 10) + racial_bonuses.get("dexterity", 0),
            constitution=score_map.get("constitution", 10) + racial_bonuses.get("constitution", 0),
            intelligence=score_map.get("intelligence", 10) + racial_bonuses.get("intelligence", 0),
            wisdom=score_map.get("wisdom", 10) + racial_bonuses.get("wisdom", 0),
            charisma=score_map.get("charisma", 10) + racial_bonuses.get("charisma", 0),
        )

        # HP
        hit_die = CLASS_HIT_DICE.get(char_class.lower(), 8)
        max_hp = hit_die + ability_scores.con_mod
        max_hp = max(1, max_hp)

        # Speed
        speed = RACIAL_SPEED.get(race, 30)

        # Armor class (from archetype)
        base_ac = archetype.get("armor_class_base", 10 + ability_scores.dex_mod)
        # Unarmored barbarian: 10 + DEX + CON
        if char_class == "Barbarian":
            base_ac = 10 + ability_scores.dex_mod + ability_scores.con_mod

        # Spell slots
        slot_data = archetype.get("spell_slots", {})
        spell_slots = SpellSlots()
        spell_slots.slots = {int(k): v for k, v in slot_data.items()}

        # Build character
        char = Character(
            discord_id=discord_id,
            name=name,
            race=race,
            char_class=char_class,
            level=1,
        )
        char.ability_scores = ability_scores
        char.max_hp = max_hp
        char.current_hp = max_hp
        char.armor_class = base_ac
        char.speed = speed
        char.proficiency_bonus = proficiency_bonus(1)
        char.hit_dice = f"1d{hit_die}"
        char.saving_throw_proficiencies = archetype.get("saving_throws", [])
        char.skill_proficiencies = archetype.get("skill_proficiencies", [])
        char.weapon_proficiencies = archetype.get("weapon_proficiencies", [])
        char.armor_proficiencies = archetype.get("armor_proficiencies", [])
        char.features = archetype.get("features", [])
        char.spell_slots = spell_slots
        char.spell_ability = archetype.get("spell_ability", "")
        char.cantrips = list(archetype.get("cantrips", []))
        char.prepared_spells = list(archetype.get("spells", []))
        char.gold = 15  # Starting gold
        char.languages = ["Common"]
        if race == "Elf":
            char.languages.append("Elvish")
        elif race == "Dwarf":
            char.languages.append("Dwarvish")
        elif race == "Halfling":
            char.languages.append("Halfling")
        elif race in ["Gnome"]:
            char.languages.append("Gnomish")

        # Starting equipment
        char.inventory = starting_equipment(char_class)
        # Equip first weapon and armor
        for item in char.inventory:
            if item.item_type == "weapon" and not any(i.equipped and i.item_type == "weapon" for i in char.inventory):
                item.equipped = True
            if item.item_type == "armor" and not any(i.equipped and i.item_type == "armor" for i in char.inventory):
                item.equipped = True

        await db.save_character(char, guild_id)

        # Post character sheet in player's private channel
        player_ch = self._player_channel(campaign, discord_id, interaction.guild)
        if player_ch:
            await player_ch.send(
                content=f"✅ **{char.name}** created! Here's your character sheet:",
                embed=character_sheet_embed(char),
            )
            if char.spell_slots.slots or char.cantrips:
                await player_ch.send(embed=spells_embed(char))
            await player_ch.send(embed=inventory_embed(char))

        rolls_text = " | ".join(str(s) for s in scores)
        await interaction.followup.send(embed=success_embed(
            f"**{name}** the {race} {char_class} created!\n"
            f"Rolled scores: {rolls_text}\n"
            f"Check your private channel for your full character sheet."
        ))

    # ------------------------------------------------------------------
    # /character sheet
    # ------------------------------------------------------------------

    @app_commands.command(name="character_sheet", description="View your character sheet")
    async def character_sheet(self, interaction: discord.Interaction):
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(
                embed=error_embed("No character found. Use `/character_create` first."), ephemeral=True
            )
            return
        await interaction.response.send_message(embed=character_sheet_embed(char), ephemeral=True)

    # ------------------------------------------------------------------
    # /character spells
    # ------------------------------------------------------------------

    @app_commands.command(name="character_spells", description="View your spells and spell slots")
    async def character_spells(self, interaction: discord.Interaction):
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return
        await interaction.response.send_message(embed=spells_embed(char), ephemeral=True)

    # ------------------------------------------------------------------
    # /character inventory
    # ------------------------------------------------------------------

    @app_commands.command(name="character_inventory", description="View your inventory")
    async def character_inventory(self, interaction: discord.Interaction):
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return
        await interaction.response.send_message(embed=inventory_embed(char), ephemeral=True)

    # ------------------------------------------------------------------
    # /character rest
    # ------------------------------------------------------------------

    @app_commands.command(name="character_rest", description="Take a short or long rest")
    @app_commands.describe(rest_type="short or long")
    async def character_rest(self, interaction: discord.Interaction, rest_type: str):
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        rest_type = rest_type.lower()
        if rest_type not in ("short", "long"):
            await interaction.response.send_message(embed=error_embed("Use 'short' or 'long'."), ephemeral=True)
            return

        if rest_type == "long":
            old_hp = char.current_hp
            char.current_hp = char.max_hp
            char.temp_hp = 0
            char.spell_slots.restore_all()
            char.death_saves = {"successes": 0, "failures": 0}
            # Restore Fighter's Second Wind, etc. (handled by description)
            msg = (
                f"**{char.name}** takes a long rest.\n"
                f"HP fully restored: {old_hp} → {char.max_hp}\n"
                f"All spell slots restored.\n"
                f"Class features refreshed."
            )
        else:
            # Short rest: spend hit dice to heal
            from engine.dice import roll_dice
            hit_die_sides = int(char.hit_dice.split("d")[1]) if "d" in char.hit_dice else 8
            healed, _ = roll_dice(f"1d{hit_die_sides}")
            healed += char.ability_scores.con_mod
            healed = max(1, healed)
            old_hp = char.current_hp
            char.heal(healed)
            msg = (
                f"**{char.name}** takes a short rest and spends a hit die.\n"
                f"Healed {healed} HP: {old_hp} → {char.current_hp}/{char.max_hp} HP"
            )

        await db.save_character(char, str(interaction.guild_id))
        await interaction.response.send_message(embed=success_embed(msg))

    # ------------------------------------------------------------------
    # /character heal (DM use)
    # ------------------------------------------------------------------

    @app_commands.command(name="character_heal", description="Heal a character (DM use)")
    @app_commands.describe(target="@mention the player", amount="HP to restore")
    async def character_heal(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        char = await db.load_character(str(target.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found for that player."), ephemeral=True)
            return

        actual = char.heal(amount)
        await db.save_character(char, str(interaction.guild_id))
        await interaction.response.send_message(embed=success_embed(
            f"**{char.name}** healed {actual} HP ({char.current_hp}/{char.max_hp} HP)."
        ))

    # ------------------------------------------------------------------
    # /character features
    # ------------------------------------------------------------------

    @app_commands.command(name="character_features", description="View your class features and traits")
    async def character_features(self, interaction: discord.Interaction):
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        features_text = "\n".join(f"• {f}" for f in char.features) if char.features else "*No features recorded.*"
        traits_text = "\n".join(f"• {t}" for t in char.traits) if char.traits else "*No traits recorded.*"
        languages_text = ", ".join(char.languages) if char.languages else "Common"
        profs = ", ".join(char.skill_proficiencies) if char.skill_proficiencies else "None"

        embed = info_embed(
            f"📚 {char.name}'s Features",
            f"**Class Features:**\n{features_text}\n\n"
            f"**Traits:**\n{traits_text}\n\n"
            f"**Languages:** {languages_text}\n"
            f"**Skill Proficiencies:** {profs}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /character actions (show available actions during combat)
    # ------------------------------------------------------------------

    @app_commands.command(name="character_actions", description="Show available actions this turn (during combat)")
    async def character_actions(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.response.send_message(
                embed=error_embed("No active combat. Use `/combat_encounter` to start one."), ephemeral=True
            )
            return

        from engine.action_validator import get_available_actions_text
        from engine.combat_engine import get_turn_tracking
        turn = get_turn_tracking(combat, discord_id)
        text = get_available_actions_text(char, turn)

        equipped = char.equipped_weapon()
        weapon_text = f"**Equipped:** {equipped.name} ({equipped.damage} {equipped.damage_type})" if equipped else ""
        full_text = f"{text}\n\n{weapon_text}" if weapon_text else text

        await interaction.response.send_message(
            embed=info_embed("🎯 Your Available Actions", full_text), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
