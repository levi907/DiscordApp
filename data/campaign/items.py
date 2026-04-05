"""
Items and equipment for Lost Mines of Phandelver.
"""
from data.models import InventoryItem


ITEM_TEMPLATES: dict[str, dict] = {
    # ------------------------------------------------------------------
    # Weapons
    # ------------------------------------------------------------------
    "shortsword": {
        "name": "Shortsword", "item_type": "weapon", "damage": "1d6",
        "damage_type": "piercing", "properties": ["finesse", "light"],
        "description": "A one-handed blade roughly two feet long.",
    },
    "longsword": {
        "name": "Longsword", "item_type": "weapon", "damage": "1d8",
        "damage_type": "slashing", "properties": ["versatile (1d10)"],
        "description": "A classic one-handed sword, versatile when wielded two-handed.",
    },
    "handaxe": {
        "name": "Handaxe", "item_type": "weapon", "damage": "1d6",
        "damage_type": "slashing", "properties": ["light", "thrown (20/60)"],
        "description": "A small axe suitable for throwing or close combat.",
    },
    "greataxe": {
        "name": "Greataxe", "item_type": "weapon", "damage": "1d12",
        "damage_type": "slashing", "properties": ["heavy", "two-handed"],
        "description": "A massive two-handed axe with fearsome cleaving power.",
    },
    "quarterstaff": {
        "name": "Quarterstaff", "item_type": "weapon", "damage": "1d6",
        "damage_type": "bludgeoning", "properties": ["versatile (1d8)"],
        "description": "A sturdy wooden staff, versatile when wielded two-handed.",
    },
    "dagger": {
        "name": "Dagger", "item_type": "weapon", "damage": "1d4",
        "damage_type": "piercing", "properties": ["finesse", "light", "thrown (20/60)"],
        "description": "A short blade, easy to conceal.",
    },
    "shortbow": {
        "name": "Shortbow", "item_type": "weapon", "damage": "1d6",
        "damage_type": "piercing", "properties": ["ammunition (80/320)", "two-handed"],
        "description": "A compact bow that fires arrows.",
    },
    "light_crossbow": {
        "name": "Light Crossbow", "item_type": "weapon", "damage": "1d8",
        "damage_type": "piercing", "properties": ["ammunition (80/320)", "loading", "two-handed"],
        "description": "A small crossbow. Requires an action to reload.",
    },
    "morningstar": {
        "name": "Morningstar", "item_type": "weapon", "damage": "1d8",
        "damage_type": "piercing", "properties": [],
        "description": "A spiked club. Brutally effective.",
    },
    "rapier": {
        "name": "Rapier", "item_type": "weapon", "damage": "1d8",
        "damage_type": "piercing", "properties": ["finesse"],
        "description": "A slender, elegant thrusting blade.",
    },

    # ------------------------------------------------------------------
    # Armor
    # ------------------------------------------------------------------
    "leather_armor": {
        "name": "Leather Armor", "item_type": "armor", "damage": "",
        "damage_type": "", "properties": ["AC 11 + DEX"],
        "description": "Stiff boiled leather. Basic protection.",
    },
    "scale_mail": {
        "name": "Scale Mail", "item_type": "armor", "damage": "",
        "damage_type": "", "properties": ["AC 14 + DEX (max 2)", "disadvantage on Stealth"],
        "description": "Overlapping metal scales affixed to leather. Clanky but sturdy.",
    },
    "chain_mail": {
        "name": "Chain Mail", "item_type": "armor", "damage": "",
        "damage_type": "", "properties": ["AC 16", "disadvantage on Stealth", "STR 13 required"],
        "description": "Interlocking metal rings. Heavy but reliable.",
    },
    "shield": {
        "name": "Shield", "item_type": "armor", "damage": "",
        "damage_type": "", "properties": ["+2 AC"],
        "description": "A wooden or metal shield worn on one arm.",
    },
    "studded_leather": {
        "name": "Studded Leather", "item_type": "armor", "damage": "",
        "damage_type": "", "properties": ["AC 12 + DEX"],
        "description": "Leather reinforced with close-set rivets.",
    },

    # ------------------------------------------------------------------
    # Adventuring gear
    # ------------------------------------------------------------------
    "torch": {
        "name": "Torch", "item_type": "misc", "damage": "", "damage_type": "",
        "properties": ["20 ft bright light, 20 ft dim for 1 hour"],
        "description": "A wooden handle with a wrapped, pitch-dipped top.",
    },
    "rope_hempen": {
        "name": "Hempen Rope (50 ft)", "item_type": "misc", "damage": "", "damage_type": "",
        "properties": [],
        "description": "Fifty feet of sturdy rope.",
    },
    "healing_potion": {
        "name": "Potion of Healing", "item_type": "consumable", "damage": "", "damage_type": "",
        "properties": ["Restore 2d4+2 HP as bonus action"],
        "description": "A small vial of rosy liquid. Drinking it restores 2d4+2 hit points.",
    },
    "antitoxin": {
        "name": "Antitoxin", "item_type": "consumable", "damage": "", "damage_type": "",
        "properties": ["Advantage on CON saves vs. poison for 1 hour"],
        "description": "A vial of medicine that counters poison.",
    },
    "caltrops": {
        "name": "Caltrops (bag of 20)", "item_type": "misc", "damage": "", "damage_type": "",
        "properties": ["Cover 5-ft square. Speed reduced to 2 on failed DC 15 DEX save."],
        "description": "Sharp metal spikes scattered on the floor to hinder pursuers.",
    },

    # ------------------------------------------------------------------
    # LMoP special items
    # ------------------------------------------------------------------
    "spider_staff": {
        "name": "Spider Staff", "item_type": "weapon", "damage": "1d6+2",
        "damage_type": "bludgeoning", "properties": ["magic", "requires attunement"],
        "description": "A gnarled staff topped with a carved spider. +2 to spell attack rolls.",
    },
    "lightbringer": {
        "name": "Lightbringer", "item_type": "weapon", "damage": "1d8+1",
        "damage_type": "radiant", "properties": ["magic", "mace", "sheds light"],
        "description": "A mace inscribed with the name 'Lightbringer.' Glows on command. +1 to attack and damage.",
    },
    "dragonguard": {
        "name": "Dragonguard", "item_type": "armor", "damage": "", "damage_type": "",
        "properties": ["magic breastplate", "+1 AC", "advantage on saves vs. dragon breath"],
        "description": "A beautifully crafted breastplate embossed with a dragon motif.",
    },
    "gauntlets_ogre_power": {
        "name": "Gauntlets of Ogre Power", "item_type": "misc", "damage": "", "damage_type": "",
        "properties": ["requires attunement", "STR becomes 19 while worn"],
        "description": "Iron gauntlets engraved with ogre faces. The wearer's strength becomes 19.",
    },
    "necklace_fireballs": {
        "name": "Necklace of Fireballs", "item_type": "misc", "damage": "", "damage_type": "",
        "properties": ["action to throw bead", "4d6 fire in 20-ft sphere (DEX DC 15 half)"],
        "description": "A necklace strung with small, glowing beads, each containing a fireball.",
    },
}


def get_item(key: str) -> InventoryItem | None:
    data = ITEM_TEMPLATES.get(key)
    if not data:
        return None
    return InventoryItem(
        name=data["name"], item_type=data["item_type"],
        damage=data.get("damage", ""), damage_type=data.get("damage_type", ""),
        properties=data.get("properties", []), description=data.get("description", ""),
    )


def starting_equipment(char_class: str) -> list[InventoryItem]:
    """Return a list of starting InventoryItems for the given class."""
    class_equipment: dict[str, list[str]] = {
        "fighter": ["chain_mail", "longsword", "shield", "handaxe", "handaxe", "healing_potion"],
        "wizard": ["quarterstaff", "dagger", "healing_potion"],
        "rogue":  ["shortsword", "shortbow", "studded_leather", "dagger", "dagger", "healing_potion"],
        "cleric": ["scale_mail", "morningstar", "shield", "healing_potion"],
        "ranger": ["scale_mail", "shortsword", "shortbow", "healing_potion"],
        "paladin": ["chain_mail", "longsword", "shield", "healing_potion"],
        "barbarian": ["greataxe", "handaxe", "handaxe", "healing_potion"],
        "bard": ["rapier", "leather_armor", "dagger", "healing_potion"],
        "druid": ["quarterstaff", "leather_armor", "healing_potion"],
        "warlock": ["light_crossbow", "leather_armor", "dagger", "healing_potion"],
        "sorcerer": ["light_crossbow", "dagger", "healing_potion"],
        "monk": ["shortsword", "dagger", "healing_potion"],
    }
    keys = class_equipment.get(char_class.lower(), ["dagger", "healing_potion"])
    return [get_item(k) for k in keys if get_item(k)]
