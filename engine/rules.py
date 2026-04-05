"""
D&D 5e rules constants and helper tables.
"""

# Ability score names
ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
ABILITY_ABBR = {
    "strength": "STR", "dexterity": "DEX", "constitution": "CON",
    "intelligence": "INT", "wisdom": "WIS", "charisma": "CHA",
    "str": "STR", "dex": "DEX", "con": "CON",
    "int": "INT", "wis": "WIS", "cha": "CHA",
}

# Skills and their governing abilities
SKILL_ABILITIES: dict[str, str] = {
    "acrobatics": "dexterity",
    "animal handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight of hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}

# Conditions and their effects (simplified for narration)
CONDITIONS: dict[str, str] = {
    "blinded": "Can't see; attacks against have advantage; your attacks have disadvantage.",
    "charmed": "Can't attack charmer; charmer has advantage on social checks.",
    "deafened": "Can't hear; fails checks requiring hearing.",
    "exhausted": "Penalty depends on level (1-6 levels).",
    "frightened": "Disadvantage on checks/attacks while source is visible; can't willingly move closer.",
    "grappled": "Speed becomes 0.",
    "incapacitated": "Can't take actions or reactions.",
    "invisible": "Can't be seen; attacks against have disadvantage; your attacks have advantage.",
    "paralyzed": "Incapacitated; fails STR/DEX saves; attacks have advantage; hits within 5 ft are critical.",
    "petrified": "Transformed to stone; incapacitated; resistance to all damage; immune to poison/disease.",
    "poisoned": "Disadvantage on attack rolls and ability checks.",
    "prone": "Disadvantage on attacks; melee attacks against have advantage; ranged attacks have disadvantage.",
    "restrained": "Speed 0; disadvantage on attacks; attacks against have advantage.",
    "stunned": "Incapacitated; fails STR/DEX saves; attacks against have advantage.",
    "unconscious": "Incapacitated, prone; attacks against have advantage; hits within 5 ft are critical.",
}

# Damage types
DAMAGE_TYPES = [
    "acid", "bludgeoning", "cold", "fire", "force", "lightning",
    "necrotic", "piercing", "poison", "psychic", "radiant",
    "slashing", "thunder",
]

# Experience point thresholds per level (1-20)
XP_THRESHOLDS = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000,
    16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000,
}

# Proficiency bonus by level
PROFICIENCY_BONUS = {
    1: 2, 2: 2, 3: 2, 4: 2,
    5: 3, 6: 3, 7: 3, 8: 3,
    9: 4, 10: 4, 11: 4, 12: 4,
    13: 5, 14: 5, 15: 5, 16: 5,
    17: 6, 18: 6, 19: 6, 20: 6,
}

# Hit dice per class
CLASS_HIT_DICE = {
    "barbarian": 12, "fighter": 10, "paladin": 10, "ranger": 10,
    "bard": 8, "cleric": 8, "druid": 8, "monk": 8, "rogue": 8, "warlock": 8,
    "sorcerer": 6, "wizard": 6,
}

# Spell slots per level per class level (simplified for LMoP classes)
SPELL_SLOTS_BY_CLASS_LEVEL: dict[str, dict[int, dict[int, int]]] = {
    "wizard": {
        1: {1: 2},
        2: {1: 3},
        3: {1: 4, 2: 2},
        4: {1: 4, 2: 3},
        5: {1: 4, 2: 3, 3: 2},
    },
    "cleric": {
        1: {1: 2},
        2: {1: 3},
        3: {1: 4, 2: 2},
        4: {1: 4, 2: 3},
        5: {1: 4, 2: 3, 3: 2},
    },
    "bard": {
        1: {1: 2},
        2: {1: 3},
        3: {1: 4, 2: 2},
        4: {1: 4, 2: 3},
        5: {1: 4, 2: 3, 3: 2},
    },
    "sorcerer": {
        1: {1: 2},
        2: {1: 3},
        3: {1: 4, 2: 2},
    },
    "warlock": {
        1: {1: 1},
        2: {1: 2},
        3: {2: 2},
        4: {2: 2},
        5: {3: 2},
    },
    "paladin": {
        2: {1: 2},
        3: {1: 3},
        4: {1: 3},
        5: {1: 4, 2: 2},
    },
    "ranger": {
        2: {1: 2},
        3: {1: 3},
        4: {1: 3},
        5: {1: 4, 2: 2},
    },
}


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    return PROFICIENCY_BONUS.get(level, 2)


def xp_for_level(level: int) -> int:
    return XP_THRESHOLDS.get(level, 0)


def level_from_xp(xp: int) -> int:
    level = 1
    for lvl, threshold in XP_THRESHOLDS.items():
        if xp >= threshold:
            level = lvl
    return level


def spell_slots_for_class(char_class: str, level: int) -> dict[int, int]:
    class_table = SPELL_SLOTS_BY_CLASS_LEVEL.get(char_class.lower(), {})
    return class_table.get(level, {})


def is_crit(roll: int) -> bool:
    return roll == 20


def is_fumble(roll: int) -> bool:
    return roll == 1
