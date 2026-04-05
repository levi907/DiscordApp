"""
Spell data for D&D 5e spells available in Lost Mines of Phandelver.
"""

SPELLS: dict[str, dict] = {
    # ------------------------------------------------------------------
    # Cantrips (level 0)
    # ------------------------------------------------------------------
    "fire bolt": {
        "name": "Fire Bolt", "level": 0, "school": "evocation",
        "casting_time": "1 action", "range": "120 feet", "components": "V, S",
        "duration": "Instantaneous",
        "description": "Hurl a mote of fire. Ranged spell attack. 1d10 fire damage (2d10 at level 5).",
        "action_type": "action", "attack_type": "ranged_spell",
        "damage": "1d10", "damage_type": "fire", "save": None,
        "upcast": {5: "2d10", 11: "3d10", 17: "4d10"},
    },
    "sacred flame": {
        "name": "Sacred Flame", "level": 0, "school": "evocation",
        "casting_time": "1 action", "range": "60 feet", "components": "V, S",
        "duration": "Instantaneous",
        "description": "Flame-like radiance descends. DC = spell save DC DEX save or 1d8 radiant.",
        "action_type": "action", "attack_type": "save",
        "damage": "1d8", "damage_type": "radiant", "save": "dexterity",
    },
    "mage hand": {
        "name": "Mage Hand", "level": 0, "school": "conjuration",
        "casting_time": "1 action", "range": "30 feet", "components": "V, S",
        "duration": "1 minute",
        "description": "Spectral hand can manipulate objects up to 10 pounds. No attack/damage.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None,
    },
    "prestidigitation": {
        "name": "Prestidigitation", "level": 0, "school": "transmutation",
        "casting_time": "1 action", "range": "10 feet", "components": "V, S",
        "duration": "Up to 1 hour",
        "description": "Minor magical tricks: light small fires, clean, create small illusions, etc.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None,
    },
    "light": {
        "name": "Light", "level": 0, "school": "evocation",
        "casting_time": "1 action", "range": "Touch", "components": "V, M (firefly)",
        "duration": "1 hour",
        "description": "Object you touch sheds bright light in a 20-foot radius.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None,
    },
    "toll the dead": {
        "name": "Toll the Dead", "level": 0, "school": "necromancy",
        "casting_time": "1 action", "range": "60 feet", "components": "V, S",
        "duration": "Instantaneous",
        "description": "DC = spell save DC WIS save or 1d8 necrotic (1d12 if target is missing HP).",
        "action_type": "action", "attack_type": "save",
        "damage": "1d8", "damage_type": "necrotic", "save": "wisdom",
    },
    "minor illusion": {
        "name": "Minor Illusion", "level": 0, "school": "illusion",
        "casting_time": "1 action", "range": "30 feet", "components": "S, M (fleece)",
        "duration": "1 minute",
        "description": "Create a sound or image of an object. Investigation check to disbelieve.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None,
    },
    "guidance": {
        "name": "Guidance", "level": 0, "school": "divination",
        "casting_time": "1 action", "range": "Touch", "components": "V, S",
        "duration": "Up to 1 minute (concentration)",
        "description": "Touch a willing creature. Once before the spell ends, add 1d4 to one ability check.",
        "action_type": "action", "attack_type": "buff",
        "damage": None, "damage_type": None, "save": None, "concentration": True,
    },
    "thaumaturgy": {
        "name": "Thaumaturgy", "level": 0, "school": "transmutation",
        "casting_time": "1 action", "range": "30 feet", "components": "V",
        "duration": "Up to 1 minute",
        "description": "Manifest minor wonder: tremor underfoot, flames flicker, doors slam, voice booms, etc.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None,
    },
    "eldritch blast": {
        "name": "Eldritch Blast", "level": 0, "school": "evocation",
        "casting_time": "1 action", "range": "120 feet", "components": "V, S",
        "duration": "Instantaneous",
        "description": "A beam of crackling energy. Ranged spell attack for 1d10 force damage.",
        "action_type": "action", "attack_type": "ranged_spell",
        "damage": "1d10", "damage_type": "force", "save": None,
    },

    # ------------------------------------------------------------------
    # Level 1
    # ------------------------------------------------------------------
    "cure wounds": {
        "name": "Cure Wounds", "level": 1, "school": "evocation",
        "casting_time": "1 action", "range": "Touch", "components": "V, S",
        "duration": "Instantaneous",
        "description": "Restore 1d8 + spellcasting modifier HP to a creature you touch.",
        "action_type": "action", "attack_type": "healing",
        "damage": "1d8", "damage_type": "healing", "save": None,
        "upcast_formula": "+1d8 per slot level above 1st",
    },
    "magic missile": {
        "name": "Magic Missile", "level": 1, "school": "evocation",
        "casting_time": "1 action", "range": "120 feet", "components": "V, S",
        "duration": "Instantaneous",
        "description": "Three darts of force, each dealing 1d4+1. Automatically hit. +1 dart per slot level above 1st.",
        "action_type": "action", "attack_type": "auto_hit",
        "damage": "1d4+1", "damage_type": "force", "save": None, "darts": 3,
        "upcast_formula": "+1 dart per slot level above 1st",
    },
    "sleep": {
        "name": "Sleep", "level": 1, "school": "enchantment",
        "casting_time": "1 action", "range": "90 feet", "components": "V, S, M (pinch of sand)",
        "duration": "1 minute",
        "description": "Roll 5d8; that many HP of creatures are put to sleep (lowest HP first). Doesn't affect undead/immune.",
        "action_type": "action", "attack_type": "special",
        "damage": None, "damage_type": None, "save": None,
    },
    "shield": {
        "name": "Shield", "level": 1, "school": "abjuration",
        "casting_time": "1 reaction", "range": "Self", "components": "V, S",
        "duration": "1 round",
        "description": "Reaction when hit or targeted by magic missile. +5 AC until start of next turn.",
        "action_type": "reaction", "attack_type": "buff",
        "damage": None, "damage_type": None, "save": None,
    },
    "thunderwave": {
        "name": "Thunderwave", "level": 1, "school": "evocation",
        "casting_time": "1 action", "range": "Self (15-foot cube)", "components": "V, S",
        "duration": "Instantaneous",
        "description": "Creatures in a 15-ft cube: DC = spell save DC CON save or 2d8 thunder + pushed 10 ft.",
        "action_type": "action", "attack_type": "save",
        "damage": "2d8", "damage_type": "thunder", "save": "constitution", "area": "15-foot cube",
        "upcast_formula": "+1d8 per slot level above 1st",
    },
    "burning hands": {
        "name": "Burning Hands", "level": 1, "school": "evocation",
        "casting_time": "1 action", "range": "Self (15-foot cone)", "components": "V, S",
        "duration": "Instantaneous",
        "description": "3d6 fire damage in a 15-ft cone. DC = spell save DC DEX save for half.",
        "action_type": "action", "attack_type": "save",
        "damage": "3d6", "damage_type": "fire", "save": "dexterity", "area": "15-foot cone",
        "upcast_formula": "+1d6 per slot level above 1st",
    },
    "healing word": {
        "name": "Healing Word", "level": 1, "school": "evocation",
        "casting_time": "1 bonus action", "range": "60 feet", "components": "V",
        "duration": "Instantaneous",
        "description": "Restore 1d4 + spellcasting modifier HP to a visible creature.",
        "action_type": "bonus_action", "attack_type": "healing",
        "damage": "1d4", "damage_type": "healing", "save": None,
        "upcast_formula": "+1d4 per slot level above 1st",
    },
    "bless": {
        "name": "Bless", "level": 1, "school": "enchantment",
        "casting_time": "1 action", "range": "30 feet", "components": "V, S, M (holy water)",
        "duration": "Up to 1 minute (concentration)",
        "description": "Up to 3 creatures add 1d4 to attack rolls and saving throws.",
        "action_type": "action", "attack_type": "buff",
        "damage": None, "damage_type": None, "save": None, "concentration": True,
    },
    "detect magic": {
        "name": "Detect Magic", "level": 1, "school": "divination",
        "casting_time": "1 action (ritual)", "range": "Self", "components": "V, S",
        "duration": "Up to 10 minutes (concentration)",
        "description": "Sense magic within 30 feet. See aura around visible magical things.",
        "action_type": "action", "attack_type": "utility",
        "damage": None, "damage_type": None, "save": None, "concentration": True,
    },
    "faerie fire": {
        "name": "Faerie Fire", "level": 1, "school": "evocation",
        "casting_time": "1 action", "range": "60 feet", "components": "V",
        "duration": "Up to 1 minute (concentration)",
        "description": "20-ft cube. DC = spell save DC DEX save or outlined in blue/green/violet light — attacks against have advantage.",
        "action_type": "action", "attack_type": "save",
        "damage": None, "damage_type": None, "save": "dexterity", "concentration": True,
    },

    # ------------------------------------------------------------------
    # Level 2
    # ------------------------------------------------------------------
    "hold person": {
        "name": "Hold Person", "level": 2, "school": "enchantment",
        "casting_time": "1 action", "range": "60 feet", "components": "V, S, M (iron bar)",
        "duration": "Up to 1 minute (concentration)",
        "description": "One humanoid: DC = spell save DC WIS save or paralyzed. Repeats save each turn.",
        "action_type": "action", "attack_type": "save",
        "damage": None, "damage_type": None, "save": "wisdom", "concentration": True,
    },
    "misty step": {
        "name": "Misty Step", "level": 2, "school": "conjuration",
        "casting_time": "1 bonus action", "range": "Self", "components": "V",
        "duration": "Instantaneous",
        "description": "Teleport up to 30 feet to an unoccupied space you can see.",
        "action_type": "bonus_action", "attack_type": "movement",
        "damage": None, "damage_type": None, "save": None,
    },
    "spiritual weapon": {
        "name": "Spiritual Weapon", "level": 2, "school": "evocation",
        "casting_time": "1 bonus action", "range": "60 feet", "components": "V, S",
        "duration": "1 minute",
        "description": "Summon spectral weapon. Bonus action: move 20 ft and make a melee spell attack for 1d8 + spellcasting modifier force damage.",
        "action_type": "bonus_action", "attack_type": "spell_weapon",
        "damage": "1d8", "damage_type": "force", "save": None,
    },

    # ------------------------------------------------------------------
    # Level 3
    # ------------------------------------------------------------------
    "fireball": {
        "name": "Fireball", "level": 3, "school": "evocation",
        "casting_time": "1 action", "range": "150 feet", "components": "V, S, M (bat guano)",
        "duration": "Instantaneous",
        "description": "8d6 fire in a 20-ft radius. DC = spell save DC DEX save for half.",
        "action_type": "action", "attack_type": "save",
        "damage": "8d6", "damage_type": "fire", "save": "dexterity", "area": "20-foot sphere",
        "upcast_formula": "+1d6 per slot level above 3rd",
    },
    "counterspell": {
        "name": "Counterspell", "level": 3, "school": "abjuration",
        "casting_time": "1 reaction", "range": "60 feet", "components": "S",
        "duration": "Instantaneous",
        "description": "Interrupt a creature casting a spell. Automatically stops spells of level 3 or lower. Higher: spellcasting ability check DC 10 + spell level.",
        "action_type": "reaction", "attack_type": "special",
        "damage": None, "damage_type": None, "save": None,
    },
}


def get_spell(name: str) -> dict | None:
    return SPELLS.get(name.lower())


def list_spells_by_level(level: int) -> list[str]:
    return [data["name"] for data in SPELLS.values() if data["level"] == level]
