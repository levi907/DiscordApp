"""
Lost Mines of Phandelver campaign data.
Chapters, locations, NPCs, encounters, and quests.
"""
from data.models import Quest

# ---------------------------------------------------------------------------
# Campaign structure
# ---------------------------------------------------------------------------

CHAPTERS = {
    1: {
        "title": "Goblin Arrows",
        "summary": (
            "The party is hired by Gundren Rockseeker to escort a wagon of supplies to Phandalin. "
            "On the Triboar Trail they discover slain horses and an ambush site — and learn Gundren "
            "and his escort Sildar Hallwinter have been captured by goblins. The trail leads to "
            "Cragmaw Hideout, a goblin cave where Sildar is held prisoner. The goblins serve Klarg, "
            "a bugbear lieutenant of the mysterious Black Spider."
        ),
        "starting_location": "Sword Coast Road",
    },
    2: {
        "title": "Phandalin",
        "summary": (
            "The party arrives at Phandalin, a frontier town rebuilding after being sacked decades ago. "
            "The Redbrands, a gang of ruffians led by Glasstaff, terrorize the townsfolk. "
            "Local quests abound — the Sleeping Giant, the Tresendar Manor ruins, and rumors of "
            "the Black Spider's agents everywhere."
        ),
        "starting_location": "Phandalin",
    },
    3: {
        "title": "The Spider's Web",
        "summary": (
            "The party investigates leads across the region: Old Owl Well, Thundertree, "
            "Wyvern Tor, and Cragmaw Castle. The Black Spider — a drow named Nezznar — "
            "seeks the Forge of Spells in Wave Echo Cave."
        ),
        "starting_location": "Phandalin",
    },
    4: {
        "title": "Wave Echo Cave",
        "summary": (
            "The party ventures into the ancient dwarven mine of Wave Echo Cave, "
            "where the Phandelver's Pact was forged. They must defeat Nezznar the Black Spider "
            "and his allies to rescue Gundren and restore the Forge of Spells."
        ),
        "starting_location": "Wave Echo Cave",
    },
}

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

LOCATIONS: dict[str, dict] = {
    "sword_coast_road": {
        "name": "Sword Coast Road",
        "description": (
            "A rutted dirt road running east through dense forest. "
            "Pine and oak crowd the verges. Birdsong is the only sound — until it stops."
        ),
        "chapter": 1,
    },
    "triboar_trail": {
        "name": "Triboar Trail",
        "description": (
            "A narrow track threading through rolling hills dotted with boulders and scrub brush. "
            "The air smells of pine resin and horse dung."
        ),
        "chapter": 1,
    },
    "goblin_ambush_site": {
        "name": "Goblin Ambush Site",
        "description": (
            "Two dead horses lie across the road, bristling with black-feathered arrows. "
            "Saddlebags have been ransacked. Goblin tracks and a drag-mark lead north into the undergrowth."
        ),
        "chapter": 1,
        "default_encounter": "goblin_ambush",
    },
    "cragmaw_hideout": {
        "name": "Cragmaw Hideout",
        "description": (
            "A shallow cave mouth hidden behind dense brush beside a cold, fast stream. "
            "The stench of goblins and unwashed fur wafts from within. "
            "Inside, a network of passages and rope bridges wind deeper into the hill."
        ),
        "chapter": 1,
        "default_encounter": "cragmaw_hideout_klarg",
    },
    "phandalin": {
        "name": "Phandalin",
        "description": (
            "A small frontier town of mud streets and timber buildings. "
            "Once destroyed by orcs, it's being rebuilt by hardscrabble settlers. "
            "A stone manor ruin looms on the eastern hill. "
            "Locals look over their shoulders whenever red-cloaked men are near."
        ),
        "chapter": 2,
        "sub_locations": [
            "Stonehill Inn", "Barthen's Provisions", "The Sleeping Giant",
            "Lionshield Coster", "Phandalin Miner's Exchange", "Shrine of Luck",
            "Townmaster's Hall", "Edermath Orchard", "Tresendar Manor",
        ],
    },
    "tresendar_manor": {
        "name": "Tresendar Manor",
        "description": (
            "The ruins of a proud stone manor on the eastern edge of Phandalin. "
            "Below it stretches a warren of cellars and crypts — the Redbrand hideout. "
            "The stink of torch smoke and stale ale drifts up through cracked flagstones."
        ),
        "chapter": 2,
        "default_encounter": "redbrand_hideout",
    },
    "old_owl_well": {
        "name": "Old Owl Well",
        "description": (
            "Ancient ruins surrounding a stone-coped well that never runs dry. "
            "A red-robed figure hunches over an open tome. "
            "Twelve zombies stand motionless nearby, staring at nothing."
        ),
        "chapter": 3,
        "default_encounter": "old_owl_well",
    },
    "wyvern_tor": {
        "name": "Wyvern Tor",
        "description": (
            "A rocky crag rising from the hills east of the Triboar Trail. "
            "Smoke rises from a cave entrance near the summit. "
            "The smell of roasting meat — and worse — hangs in the air."
        ),
        "chapter": 3,
        "default_encounter": "orc_camp",
    },
    "thundertree": {
        "name": "Thundertree",
        "description": (
            "The ruined village of Thundertree, abandoned after a volcanic eruption. "
            "Ash-choked streets between crumbling stone walls. "
            "Strange twig blights shuffle between the ruins, and something massive lurks "
            "in the tower at the village center."
        ),
        "chapter": 3,
        "default_encounter": "thundertree_dragon",
    },
    "cragmaw_castle": {
        "name": "Cragmaw Castle",
        "description": (
            "A ruined castle half-swallowed by forest. Walls crumble, towers lean. "
            "Goblin sentries pick their noses on the battlements. "
            "Inside: the bugbear king Grol holds court."
        ),
        "chapter": 3,
        "default_encounter": "cragmaw_castle_grol",
    },
    "wave_echo_cave": {
        "name": "Wave Echo Cave",
        "description": (
            "A vast underground complex ringing with the thunder of an underground sea. "
            "Ancient dwarven and gnomish stonework crumbles amid modern monster lairs. "
            "The air smells of salt and old magic. "
            "Somewhere in the depths, the Forge of Spells awaits."
        ),
        "chapter": 4,
        "default_encounter": "wave_echo_cave_black_spider",
    },
}

# ---------------------------------------------------------------------------
# NPCs
# ---------------------------------------------------------------------------

NPCS: dict[str, dict] = {
    "gundren_rockseeker": {
        "name": "Gundren Rockseeker",
        "description": "A stout dwarf merchant with an infectious laugh and a secret: he's found the entrance to Wave Echo Cave.",
        "role": "quest_giver",
        "location": "cragmaw_castle",  # captured
    },
    "sildar_hallwinter": {
        "name": "Sildar Hallwinter",
        "description": "A veteran warrior in his fifties, a member of the Lords' Alliance. Captured by goblins, grateful to be rescued.",
        "role": "ally",
        "location": "cragmaw_hideout",  # captured at start
    },
    "elmar_barthen": {
        "name": "Elmar Barthen",
        "description": "The cheerful proprietor of Barthen's Provisions. He's expecting Gundren's wagon.",
        "role": "merchant",
        "location": "phandalin",
    },
    "toblen_stonehill": {
        "name": "Toblen Stonehill",
        "description": "The nervous innkeeper of the Stonehill Inn. Has his ear to the ground.",
        "role": "innkeeper",
        "location": "phandalin",
    },
    "halia_thornton": {
        "name": "Halia Thornton",
        "description": "The sharp-eyed owner of the Phandalin Miner's Exchange. Secretly wants to take over the Redbrands.",
        "role": "merchant",
        "location": "phandalin",
    },
    "daran_edermath": {
        "name": "Daran Edermath",
        "description": "A retired half-elf adventurer who tends an apple orchard. Old Harper. Has a quest about Old Owl Well.",
        "role": "quest_giver",
        "location": "phandalin",
    },
    "linene_graywind": {
        "name": "Linene Graywind",
        "description": "The sharp businesswoman running the Lionshield Coster trading post.",
        "role": "merchant",
        "location": "phandalin",
    },
    "harbin_wester": {
        "name": "Harbin Wester",
        "description": "The pudgy, cowardly Townmaster of Phandalin. Refuses to act against the Redbrands.",
        "role": "townmaster",
        "location": "phandalin",
    },
    "reidoth": {
        "name": "Reidoth the Druid",
        "description": "A weather-beaten wood elf druid who haunts the ruins of Thundertree. Knows the location of Cragmaw Castle.",
        "role": "quest_giver",
        "location": "thundertree",
    },
    "nezznar": {
        "name": "Nezznar the Black Spider",
        "description": "A drow mage, the campaign's primary villain. Obsessed with the Forge of Spells. Uses spider minions.",
        "role": "villain",
        "location": "wave_echo_cave",
    },
}

# ---------------------------------------------------------------------------
# Encounters (by chapter/location)
# ---------------------------------------------------------------------------

ENCOUNTERS: dict[str, dict] = {
    "goblin_ambush": {
        "name": "Goblin Ambush",
        "location": "goblin_ambush_site",
        "chapter": 1,
        "monsters": [
            {"key": "goblin", "count": 4},
        ],
        "description": (
            "Goblins burst from the brush on both sides of the road, arrows nocked. "
            "'Kill them all!' one shrieks in Goblin."
        ),
        "xp": 200,
        "loot": [{"name": "Gold pieces", "quantity": 10}, {"name": "Shortbow", "quantity": 1}],
    },
    "cragmaw_hideout_entry": {
        "name": "Cragmaw Hideout — Guard Post",
        "location": "cragmaw_hideout",
        "chapter": 1,
        "monsters": [
            {"key": "goblin", "count": 3},
            {"key": "wolf", "count": 2},
        ],
        "description": (
            "The cave widens into a chamber lit by a guttering fire. "
            "Wolves strain at chains as goblins bark orders."
        ),
        "xp": 250,
    },
    "cragmaw_hideout_klarg": {
        "name": "Cragmaw Hideout — Klarg's Den",
        "location": "cragmaw_hideout",
        "chapter": 1,
        "monsters": [
            {"key": "klarg", "count": 1},
            {"key": "goblin", "count": 2},
            {"key": "wolf", "count": 1},
        ],
        "description": (
            "A massive bugbear reclines on a makeshift throne of crates and barrels. "
            "'More food for Klarg!' he bellows, grinning at his followers."
        ),
        "xp": 400,
        "loot": [
            {"name": "Gold pieces", "quantity": 25},
            {"name": "Healing Potion", "quantity": 2},
        ],
        "story_flag": "klarg_defeated",
    },
    "redbrand_hideout": {
        "name": "Tresendar Manor — Redbrand Hideout",
        "location": "tresendar_manor",
        "chapter": 2,
        "monsters": [
            {"key": "redbrand_ruffian", "count": 4},
            {"key": "nothic", "count": 1},
            {"key": "glasstaff", "count": 1},
        ],
        "description": (
            "The cellar beneath Tresendar Manor. Torchlight flickers on stone walls. "
            "A one-eyed creature lurks in a pit, muttering. "
            "Redbrands lounge on crates, playing dice."
        ),
        "xp": 950,
        "loot": [
            {"name": "Gold pieces", "quantity": 180},
            {"name": "Spider Staff", "quantity": 1},
            {"name": "Healing Potion", "quantity": 3},
        ],
        "story_flag": "glasstaff_defeated",
    },
    "old_owl_well": {
        "name": "Old Owl Well — Undead Guard",
        "location": "old_owl_well",
        "chapter": 3,
        "monsters": [
            {"key": "zombie", "count": 12},
        ],
        "description": (
            "Twelve zombies turn their hollow gazes on the party. "
            "Behind them, a wizard in red robes watches with detached curiosity."
        ),
        "xp": 600,
    },
    "orc_camp": {
        "name": "Wyvern Tor — Orc Camp",
        "location": "wyvern_tor",
        "chapter": 3,
        "monsters": [
            {"key": "hobgoblin", "count": 3},
            {"key": "bugbear", "count": 1},
        ],
        "description": (
            "A band of orcs and their bugbear leader camp at the base of the tor, "
            "raiding the surrounding countryside."
        ),
        "xp": 500,
        "loot": [{"name": "Gold pieces", "quantity": 55}],
    },
    "wave_echo_cave_black_spider": {
        "name": "Wave Echo Cave — The Forge of Spells",
        "location": "wave_echo_cave",
        "chapter": 4,
        "monsters": [
            {"key": "black_spider", "count": 1},
            {"key": "giant_spider", "count": 2},
            {"key": "flameskull", "count": 1},
        ],
        "description": (
            "The Forge of Spells — a raised stone dais crackling with magical fire. "
            "A drow in spider-silk robes turns from the forge, his eight spider companions "
            "scuttling toward you. 'You're too late,' Nezznar says softly."
        ),
        "xp": 2600,
        "loot": [
            {"name": "Lightbringer", "quantity": 1},
            {"name": "Dragonguard", "quantity": 1},
            {"name": "Gauntlets of Ogre Power", "quantity": 1},
            {"name": "Gold pieces", "quantity": 500},
        ],
        "story_flag": "black_spider_defeated",
    },
}

# ---------------------------------------------------------------------------
# Starting quests
# ---------------------------------------------------------------------------

STARTING_QUESTS = [
    Quest(
        quest_id="main_escort",
        title="Escort to Phandalin",
        description=(
            "Gundren Rockseeker hired you to escort a wagon of supplies from Neverwinter to Phandalin. "
            "He rode ahead with his bodyguard Sildar Hallwinter. Deliver the goods to Barthen's Provisions."
        ),
        objectives=[
            {"text": "Deliver the wagon to Barthen's Provisions in Phandalin", "completed": False},
        ],
        rewards={"gold": 10, "description": "10 gp each upon delivery"},
        location="phandalin",
        giver="Gundren Rockseeker",
    ),
    Quest(
        quest_id="main_gundren",
        title="Find Gundren Rockseeker",
        description=(
            "Gundren and Sildar were ambushed by goblins on the Triboar Trail. "
            "Follow the goblin trail and rescue them."
        ),
        objectives=[
            {"text": "Investigate the ambush site", "completed": False},
            {"text": "Rescue Sildar Hallwinter", "completed": False},
            {"text": "Find and rescue Gundren Rockseeker", "completed": False},
        ],
        rewards={"gold": 0, "description": "Sildar will pay 50 gp for safe return to Phandalin"},
        location="cragmaw_hideout",
        giver="Sildar Hallwinter",
    ),
]

# ---------------------------------------------------------------------------
# Character class archetypes for LMoP (level 1 starting stats)
# ---------------------------------------------------------------------------

CLASS_ARCHETYPES: dict[str, dict] = {
    "fighter": {
        "hit_dice": "1d10",
        "max_hp_base": 10,
        "armor_class_base": 16,  # chain mail
        "saving_throws": ["strength", "constitution"],
        "skill_proficiencies": ["Athletics", "Perception"],
        "armor_proficiencies": ["Light", "Medium", "Heavy", "Shields"],
        "weapon_proficiencies": ["Simple", "Martial"],
        "features": ["Second Wind (1d10+level HP, bonus action, 1/short rest)", "Fighting Style"],
        "spell_ability": "",
        "spell_slots": {},
        "cantrips": [],
    },
    "wizard": {
        "hit_dice": "1d6",
        "max_hp_base": 6,
        "armor_class_base": 12,  # dex 14
        "saving_throws": ["intelligence", "wisdom"],
        "skill_proficiencies": ["Arcana", "History"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light Crossbows"],
        "features": ["Arcane Recovery (regain spell slots on short rest, up to level/2 total)"],
        "spell_ability": "intelligence",
        "spell_slots": {1: 2},
        "cantrips": ["fire bolt", "minor illusion", "prestidigitation"],
        "spells": ["magic missile", "burning hands", "detect magic", "sleep"],
    },
    "rogue": {
        "hit_dice": "1d8",
        "max_hp_base": 8,
        "armor_class_base": 14,  # studded leather + dex 14
        "saving_throws": ["dexterity", "intelligence"],
        "skill_proficiencies": ["Stealth", "Acrobatics", "Sleight of Hand", "Perception"],
        "armor_proficiencies": ["Light"],
        "weapon_proficiencies": ["Simple", "Hand Crossbows", "Longswords", "Rapiers", "Shortswords"],
        "features": [
            "Sneak Attack (1d6 extra damage with advantage or flanking ally)",
            "Thieves' Cant",
            "Expertise (double proficiency in 2 skills)",
        ],
        "spell_ability": "",
        "spell_slots": {},
        "cantrips": [],
    },
    "cleric": {
        "hit_dice": "1d8",
        "max_hp_base": 8,
        "armor_class_base": 18,  # scale mail + shield
        "saving_throws": ["wisdom", "charisma"],
        "skill_proficiencies": ["Insight", "Religion"],
        "armor_proficiencies": ["Light", "Medium", "Shields"],
        "weapon_proficiencies": ["Simple"],
        "features": [
            "Spellcasting (Wisdom)",
            "Divine Domain (Life: Disciple of Life — heals extra HP equal to 2 + spell level)",
        ],
        "spell_ability": "wisdom",
        "spell_slots": {1: 2},
        "cantrips": ["sacred flame", "thaumaturgy", "guidance"],
        "spells": ["cure wounds", "bless", "healing word", "detect magic"],
    },
    "ranger": {
        "hit_dice": "1d10",
        "max_hp_base": 10,
        "armor_class_base": 14,  # scale mail
        "saving_throws": ["strength", "dexterity"],
        "skill_proficiencies": ["Perception", "Stealth", "Survival"],
        "armor_proficiencies": ["Light", "Medium", "Shields"],
        "weapon_proficiencies": ["Simple", "Martial"],
        "features": [
            "Favored Enemy (choose one type, advantage on Survival to track)",
            "Natural Explorer (choose one terrain type, various bonuses)",
        ],
        "spell_ability": "wisdom",
        "spell_slots": {},  # spells at level 2
        "cantrips": [],
    },
    "paladin": {
        "hit_dice": "1d10",
        "max_hp_base": 10,
        "armor_class_base": 18,  # chain mail + shield
        "saving_throws": ["wisdom", "charisma"],
        "skill_proficiencies": ["Athletics", "Persuasion"],
        "armor_proficiencies": ["Light", "Medium", "Heavy", "Shields"],
        "weapon_proficiencies": ["Simple", "Martial"],
        "features": [
            "Divine Sense (detect celestials/undead/fiends within 60 ft, CHA mod + 1 times per long rest)",
            "Lay on Hands (heal up to 5 HP total per long rest, action)",
        ],
        "spell_ability": "charisma",
        "spell_slots": {},  # spells at level 2
        "cantrips": [],
    },
    "barbarian": {
        "hit_dice": "1d12",
        "max_hp_base": 12,
        "armor_class_base": 13,  # unarmored: 10 + CON
        "saving_throws": ["strength", "constitution"],
        "skill_proficiencies": ["Athletics", "Perception"],
        "armor_proficiencies": ["Light", "Medium", "Shields"],
        "weapon_proficiencies": ["Simple", "Martial"],
        "features": [
            "Rage (bonus action, advantage on STR checks/saves, +2 damage with STR weapons, resistance to B/P/S, 2/long rest)",
            "Unarmored Defense (AC = 10 + DEX + CON when not wearing armor)",
        ],
        "spell_ability": "",
        "spell_slots": {},
        "cantrips": [],
    },
    "bard": {
        "hit_dice": "1d8",
        "max_hp_base": 8,
        "armor_class_base": 13,  # leather + dex
        "saving_throws": ["dexterity", "charisma"],
        "skill_proficiencies": ["Acrobatics", "Performance", "Persuasion"],
        "armor_proficiencies": ["Light"],
        "weapon_proficiencies": ["Simple", "Hand Crossbows", "Longswords", "Rapiers", "Shortswords"],
        "features": [
            "Spellcasting (Charisma)",
            "Bardic Inspiration (give 1d6 to ally as bonus action, CHA mod times per long rest)",
        ],
        "spell_ability": "charisma",
        "spell_slots": {1: 2},
        "cantrips": ["minor illusion", "prestidigitation"],
        "spells": ["healing word", "faerie fire", "sleep"],
    },
}


def get_encounter(encounter_key: str) -> dict | None:
    return ENCOUNTERS.get(encounter_key)


def get_location(location_key: str) -> dict | None:
    return LOCATIONS.get(location_key)


def get_npc(npc_key: str) -> dict | None:
    return NPCS.get(npc_key)


def get_class_archetype(char_class: str) -> dict | None:
    return CLASS_ARCHETYPES.get(char_class.lower())
