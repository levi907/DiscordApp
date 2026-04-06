"""
Data models for the D&D Discord bot.
All game state is represented as dataclasses and serialized to/from SQLite.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json


# ---------------------------------------------------------------------------
# Character / Player
# ---------------------------------------------------------------------------

@dataclass
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def modifier(self, score: int) -> int:
        return (score - 10) // 2

    @property
    def str_mod(self): return self.modifier(self.strength)
    @property
    def dex_mod(self): return self.modifier(self.dexterity)
    @property
    def con_mod(self): return self.modifier(self.constitution)
    @property
    def int_mod(self): return self.modifier(self.intelligence)
    @property
    def wis_mod(self): return self.modifier(self.wisdom)
    @property
    def cha_mod(self): return self.modifier(self.charisma)

    def to_dict(self) -> dict:
        return {
            "strength": self.strength, "dexterity": self.dexterity,
            "constitution": self.constitution, "intelligence": self.intelligence,
            "wisdom": self.wisdom, "charisma": self.charisma,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AbilityScores:
        return cls(**d)


@dataclass
class SpellSlots:
    """Tracks spell slots by level (1-9)."""
    slots: dict[int, int] = field(default_factory=dict)       # level -> max
    used: dict[int, int] = field(default_factory=dict)        # level -> used

    def available(self, level: int) -> int:
        return max(0, self.slots.get(level, 0) - self.used.get(level, 0))

    def expend(self, level: int) -> bool:
        if self.available(level) > 0:
            self.used[level] = self.used.get(level, 0) + 1
            return True
        return False

    def restore_all(self):
        self.used = {}

    def to_dict(self) -> dict:
        return {"slots": self.slots, "used": self.used}

    @classmethod
    def from_dict(cls, d: dict) -> SpellSlots:
        obj = cls()
        obj.slots = {int(k): v for k, v in d.get("slots", {}).items()}
        obj.used = {int(k): v for k, v in d.get("used", {}).items()}
        return obj


@dataclass
class InventoryItem:
    name: str
    quantity: int = 1
    equipped: bool = False
    description: str = ""
    item_type: str = "misc"   # weapon, armor, consumable, misc
    damage: str = ""          # e.g. "1d6+2"
    damage_type: str = ""
    properties: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "quantity": self.quantity,
            "equipped": self.equipped, "description": self.description,
            "item_type": self.item_type, "damage": self.damage,
            "damage_type": self.damage_type, "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, d: dict) -> InventoryItem:
        return cls(
            name=d["name"], quantity=d.get("quantity", 1),
            equipped=d.get("equipped", False), description=d.get("description", ""),
            item_type=d.get("item_type", "misc"), damage=d.get("damage", ""),
            damage_type=d.get("damage_type", ""), properties=d.get("properties", []),
        )


@dataclass
class Character:
    discord_id: str
    name: str
    race: str
    char_class: str
    level: int = 1
    background: str = ""
    alignment: str = "Neutral"

    # Core stats
    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    max_hp: int = 10
    current_hp: int = 10
    temp_hp: int = 0
    armor_class: int = 10
    speed: int = 30
    proficiency_bonus: int = 2
    hit_dice: str = "1d8"

    # Proficiencies
    saving_throw_proficiencies: list[str] = field(default_factory=list)
    skill_proficiencies: list[str] = field(default_factory=list)
    weapon_proficiencies: list[str] = field(default_factory=list)
    armor_proficiencies: list[str] = field(default_factory=list)

    # Resources
    spell_slots: SpellSlots = field(default_factory=SpellSlots)
    known_spells: list[str] = field(default_factory=list)
    prepared_spells: list[str] = field(default_factory=list)
    cantrips: list[str] = field(default_factory=list)
    spell_ability: str = ""  # "intelligence", "wisdom", "charisma"

    # Features and traits
    features: list[str] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    # Inventory
    inventory: list[InventoryItem] = field(default_factory=list)
    gold: int = 0

    # Status
    conditions: list[str] = field(default_factory=list)  # poisoned, blinded, etc.
    death_saves: dict[str, int] = field(default_factory=lambda: {"successes": 0, "failures": 0})

    # Experience
    experience_points: int = 0

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def is_unconscious(self) -> bool:
        return self.current_hp <= 0 and self.death_saves["failures"] < 3

    def is_dead(self) -> bool:
        return self.death_saves["failures"] >= 3

    def take_damage(self, amount: int, damage_type: str = "") -> str:
        """Apply damage, return description of what happened."""
        # Apply temp HP first
        if self.temp_hp > 0:
            absorbed = min(self.temp_hp, amount)
            self.temp_hp -= absorbed
            amount -= absorbed

        self.current_hp = max(0, self.current_hp - amount)

        if self.current_hp == 0:
            return "falls unconscious"
        return f"has {self.current_hp}/{self.max_hp} HP remaining"

    def heal(self, amount: int) -> int:
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - old_hp

    def spell_attack_bonus(self) -> int:
        mod_map = {
            "intelligence": self.ability_scores.int_mod,
            "wisdom": self.ability_scores.wis_mod,
            "charisma": self.ability_scores.cha_mod,
        }
        mod = mod_map.get(self.spell_ability, 0)
        return mod + self.proficiency_bonus

    def spell_save_dc(self) -> int:
        return 8 + self.spell_attack_bonus()

    def equipped_weapon(self) -> Optional[InventoryItem]:
        for item in self.inventory:
            if item.equipped and item.item_type == "weapon":
                return item
        return None

    def to_dict(self) -> dict:
        return {
            "discord_id": self.discord_id,
            "name": self.name,
            "race": self.race,
            "char_class": self.char_class,
            "level": self.level,
            "background": self.background,
            "alignment": self.alignment,
            "ability_scores": self.ability_scores.to_dict(),
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "temp_hp": self.temp_hp,
            "armor_class": self.armor_class,
            "speed": self.speed,
            "proficiency_bonus": self.proficiency_bonus,
            "hit_dice": self.hit_dice,
            "saving_throw_proficiencies": self.saving_throw_proficiencies,
            "skill_proficiencies": self.skill_proficiencies,
            "weapon_proficiencies": self.weapon_proficiencies,
            "armor_proficiencies": self.armor_proficiencies,
            "spell_slots": self.spell_slots.to_dict(),
            "known_spells": self.known_spells,
            "prepared_spells": self.prepared_spells,
            "cantrips": self.cantrips,
            "spell_ability": self.spell_ability,
            "features": self.features,
            "traits": self.traits,
            "languages": self.languages,
            "inventory": [i.to_dict() for i in self.inventory],
            "gold": self.gold,
            "conditions": self.conditions,
            "death_saves": self.death_saves,
            "experience_points": self.experience_points,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Character:
        c = cls(
            discord_id=d["discord_id"],
            name=d["name"],
            race=d["race"],
            char_class=d["char_class"],
        )
        c.level = d.get("level", 1)
        c.background = d.get("background", "")
        c.alignment = d.get("alignment", "Neutral")
        c.ability_scores = AbilityScores.from_dict(d.get("ability_scores", {}))
        c.max_hp = d.get("max_hp", 10)
        c.current_hp = d.get("current_hp", 10)
        c.temp_hp = d.get("temp_hp", 0)
        c.armor_class = d.get("armor_class", 10)
        c.speed = d.get("speed", 30)
        c.proficiency_bonus = d.get("proficiency_bonus", 2)
        c.hit_dice = d.get("hit_dice", "1d8")
        c.saving_throw_proficiencies = d.get("saving_throw_proficiencies", [])
        c.skill_proficiencies = d.get("skill_proficiencies", [])
        c.weapon_proficiencies = d.get("weapon_proficiencies", [])
        c.armor_proficiencies = d.get("armor_proficiencies", [])
        c.spell_slots = SpellSlots.from_dict(d.get("spell_slots", {}))
        c.known_spells = d.get("known_spells", [])
        c.prepared_spells = d.get("prepared_spells", [])
        c.cantrips = d.get("cantrips", [])
        c.spell_ability = d.get("spell_ability", "")
        c.features = d.get("features", [])
        c.traits = d.get("traits", [])
        c.languages = d.get("languages", [])
        c.inventory = [InventoryItem.from_dict(i) for i in d.get("inventory", [])]
        c.gold = d.get("gold", 0)
        c.conditions = d.get("conditions", [])
        c.death_saves = d.get("death_saves", {"successes": 0, "failures": 0})
        c.experience_points = d.get("experience_points", 0)
        return c


# ---------------------------------------------------------------------------
# Monsters / Combatants
# ---------------------------------------------------------------------------

@dataclass
class Monster:
    name: str
    max_hp: int
    current_hp: int
    armor_class: int
    speed: int
    challenge_rating: float
    experience_points: int

    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    conditions: list[str] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)  # list of action dicts
    legendary_actions: list[dict] = field(default_factory=list)
    damage_resistances: list[str] = field(default_factory=list)
    damage_immunities: list[str] = field(default_factory=list)
    condition_immunities: list[str] = field(default_factory=list)
    senses: dict = field(default_factory=dict)
    description: str = ""
    monster_id: str = ""  # unique in combat (e.g. "goblin_1")

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def take_damage(self, amount: int, damage_type: str = "") -> str:
        if damage_type in self.damage_immunities:
            return f"is immune to {damage_type} damage"
        if damage_type in self.damage_resistances:
            amount = amount // 2
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp == 0:
            return "is slain"
        return f"has {self.current_hp}/{self.max_hp} HP remaining"

    def to_dict(self) -> dict:
        return {
            "name": self.name, "max_hp": self.max_hp, "current_hp": self.current_hp,
            "armor_class": self.armor_class, "speed": self.speed,
            "challenge_rating": self.challenge_rating, "experience_points": self.experience_points,
            "ability_scores": self.ability_scores.to_dict(),
            "conditions": self.conditions, "actions": self.actions,
            "legendary_actions": self.legendary_actions,
            "damage_resistances": self.damage_resistances,
            "damage_immunities": self.damage_immunities,
            "condition_immunities": self.condition_immunities,
            "senses": self.senses, "description": self.description,
            "monster_id": self.monster_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Monster:
        m = cls(
            name=d["name"], max_hp=d["max_hp"], current_hp=d.get("current_hp", d["max_hp"]),
            armor_class=d["armor_class"], speed=d.get("speed", 30),
            challenge_rating=d.get("challenge_rating", 0),
            experience_points=d.get("experience_points", 0),
        )
        m.ability_scores = AbilityScores.from_dict(d.get("ability_scores", {}))
        m.conditions = d.get("conditions", [])
        m.actions = d.get("actions", [])
        m.legendary_actions = d.get("legendary_actions", [])
        m.damage_resistances = d.get("damage_resistances", [])
        m.damage_immunities = d.get("damage_immunities", [])
        m.condition_immunities = d.get("condition_immunities", [])
        m.senses = d.get("senses", {})
        m.description = d.get("description", "")
        m.monster_id = d.get("monster_id", m.name.lower().replace(" ", "_"))
        return m


# ---------------------------------------------------------------------------
# Combat State
# ---------------------------------------------------------------------------

@dataclass
class CombatantTurn:
    """Tracks what actions a combatant has used this turn."""
    action_used: bool = False
    bonus_action_used: bool = False
    movement_used: int = 0     # feet moved
    reaction_used: bool = False

    def reset(self):
        self.action_used = False
        self.bonus_action_used = False
        self.movement_used = 0
        self.reaction_used = False

    def to_dict(self) -> dict:
        return {
            "action_used": self.action_used,
            "bonus_action_used": self.bonus_action_used,
            "movement_used": self.movement_used,
            "reaction_used": self.reaction_used,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CombatantTurn:
        return cls(
            action_used=d.get("action_used", False),
            bonus_action_used=d.get("bonus_action_used", False),
            movement_used=d.get("movement_used", 0),
            reaction_used=d.get("reaction_used", False),
        )


@dataclass
class CombatState:
    """Full combat encounter state."""
    encounter_id: str
    round_number: int = 1
    active_index: int = 0       # index into initiative_order
    is_active: bool = False
    encounter_name: str = ""
    encounter_key: str = ""     # LMOP encounter key (e.g. "goblin_ambush")
    location: str = ""

    # initiative_order: list of combatant IDs in order
    initiative_order: list[str] = field(default_factory=list)
    # initiative_rolls: combatant_id -> roll total
    initiative_rolls: dict[str, int] = field(default_factory=dict)

    # Combatants: combatant_id -> dict (character or monster)
    players: dict[str, dict] = field(default_factory=dict)     # discord_id -> char dict
    monsters: dict[str, dict] = field(default_factory=dict)    # monster_id -> monster dict

    # Turn tracking: combatant_id -> CombatantTurn dict
    turn_tracking: dict[str, dict] = field(default_factory=dict)

    # Combat log for this encounter
    combat_log: list[str] = field(default_factory=list)

    def current_combatant_id(self) -> Optional[str]:
        if not self.initiative_order:
            return None
        return self.initiative_order[self.active_index % len(self.initiative_order)]

    def advance_turn(self):
        current_id = self.current_combatant_id()
        if current_id and current_id in self.turn_tracking:
            self.turn_tracking[current_id] = CombatantTurn().to_dict()

        self.active_index += 1
        if self.active_index >= len(self.initiative_order):
            self.active_index = 0
            self.round_number += 1

    def add_log(self, entry: str):
        self.combat_log.append(f"[Round {self.round_number}] {entry}")

    def to_dict(self) -> dict:
        return {
            "encounter_id": self.encounter_id,
            "round_number": self.round_number,
            "active_index": self.active_index,
            "is_active": self.is_active,
            "encounter_name": self.encounter_name,
            "encounter_key": self.encounter_key,
            "location": self.location,
            "initiative_order": self.initiative_order,
            "initiative_rolls": self.initiative_rolls,
            "players": self.players,
            "monsters": self.monsters,
            "turn_tracking": self.turn_tracking,
            "combat_log": self.combat_log,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CombatState:
        c = cls(encounter_id=d["encounter_id"])
        c.round_number = d.get("round_number", 1)
        c.active_index = d.get("active_index", 0)
        c.is_active = d.get("is_active", False)
        c.encounter_name = d.get("encounter_name", "")
        c.encounter_key = d.get("encounter_key", "")
        c.location = d.get("location", "")
        c.initiative_order = d.get("initiative_order", [])
        c.initiative_rolls = d.get("initiative_rolls", {})
        c.players = d.get("players", {})
        c.monsters = d.get("monsters", {})
        c.turn_tracking = d.get("turn_tracking", {})
        c.combat_log = d.get("combat_log", [])
        return c


# ---------------------------------------------------------------------------
# Quest / Campaign
# ---------------------------------------------------------------------------

@dataclass
class Quest:
    quest_id: str
    title: str
    description: str
    status: str = "active"   # active, completed, failed
    objectives: list[dict] = field(default_factory=list)  # {"text": ..., "completed": bool}
    rewards: dict = field(default_factory=dict)
    location: str = ""
    giver: str = ""

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id, "title": self.title,
            "description": self.description, "status": self.status,
            "objectives": self.objectives, "rewards": self.rewards,
            "location": self.location, "giver": self.giver,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Quest:
        return cls(
            quest_id=d["quest_id"], title=d["title"],
            description=d["description"], status=d.get("status", "active"),
            objectives=d.get("objectives", []), rewards=d.get("rewards", {}),
            location=d.get("location", ""), giver=d.get("giver", ""),
        )


@dataclass
class CampaignState:
    """Tracks overall campaign progress."""
    guild_id: str
    campaign_name: str = "Lost Mines of Phandelver"
    chapter: int = 1
    current_location: str = "Sword Coast Road"
    session_number: int = 1

    # Channel IDs
    narration_channel_id: str = ""
    log_channel_id: str = ""
    player_channel_ids: dict[str, str] = field(default_factory=dict)  # discord_id -> channel_id
    category_id: str = ""

    # Players in the campaign
    player_ids: list[str] = field(default_factory=list)

    # Quests
    quests: list[dict] = field(default_factory=list)

    # Campaign summary / history
    session_summaries: list[str] = field(default_factory=list)
    important_npcs: dict[str, str] = field(default_factory=dict)  # name -> description
    discovered_locations: list[str] = field(default_factory=list)

    # Active combat
    active_combat: Optional[dict] = None

    # Campaign flags for story progression
    story_flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "campaign_name": self.campaign_name,
            "chapter": self.chapter,
            "current_location": self.current_location,
            "session_number": self.session_number,
            "narration_channel_id": self.narration_channel_id,
            "log_channel_id": self.log_channel_id,
            "player_channel_ids": self.player_channel_ids,
            "category_id": self.category_id,
            "player_ids": self.player_ids,
            "quests": self.quests,
            "session_summaries": self.session_summaries,
            "important_npcs": self.important_npcs,
            "discovered_locations": self.discovered_locations,
            "active_combat": self.active_combat,
            "story_flags": self.story_flags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CampaignState:
        c = cls(guild_id=d["guild_id"])
        c.campaign_name = d.get("campaign_name", "Lost Mines of Phandelver")
        c.chapter = d.get("chapter", 1)
        c.current_location = d.get("current_location", "Sword Coast Road")
        c.session_number = d.get("session_number", 1)
        c.narration_channel_id = d.get("narration_channel_id", "")
        c.log_channel_id = d.get("log_channel_id", "")
        c.player_channel_ids = d.get("player_channel_ids", {})
        c.category_id = d.get("category_id", "")
        c.player_ids = d.get("player_ids", [])
        c.quests = d.get("quests", [])
        c.session_summaries = d.get("session_summaries", [])
        c.important_npcs = d.get("important_npcs", {})
        c.discovered_locations = d.get("discovered_locations", [])
        c.active_combat = d.get("active_combat")
        c.story_flags = d.get("story_flags", {})
        return c
