"""
Monster stat blocks for Lost Mines of Phandelver.
All values based on D&D 5e SRD.
"""
from data.models import Monster, AbilityScores


def _make(name, hp, ac, speed, cr, xp, str_, dex, con, int_, wis, cha,
          actions=None, resistances=None, immunities=None, cond_immunities=None,
          senses=None, description="", monster_id=""):
    m = Monster(
        name=name, max_hp=hp, current_hp=hp, armor_class=ac, speed=speed,
        challenge_rating=cr, experience_points=xp, description=description,
        monster_id=monster_id or name.lower().replace(" ", "_"),
    )
    m.ability_scores = AbilityScores(str_, dex, con, int_, wis, cha)
    m.actions = actions or []
    m.damage_resistances = resistances or []
    m.damage_immunities = immunities or []
    m.condition_immunities = cond_immunities or []
    m.senses = senses or {}
    return m


MONSTER_TEMPLATES: dict[str, dict] = {
    # ------------------------------------------------------------------ CR 1/4
    "goblin": _make(
        "Goblin", hp=7, ac=15, speed=30, cr=0.25, xp=50,
        str_=8, dex=14, con=10, int_=10, wis=8, cha=8,
        actions=[
            {"name": "Scimitar", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d6+2", "damage_type": "slashing", "reach": 5},
            {"name": "Shortbow", "type": "ranged_attack", "attack_bonus": 4,
             "damage": "1d6+2", "damage_type": "piercing", "range": "80/320"},
        ],
        description="A sneaky, small humanoid with yellowy-green skin and sharp teeth.",
    ).to_dict(),

    "skeleton": _make(
        "Skeleton", hp=13, ac=13, speed=30, cr=0.25, xp=50,
        str_=10, dex=14, con=15, int_=6, wis=8, cha=5,
        actions=[
            {"name": "Shortsword", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d6+2", "damage_type": "piercing", "reach": 5},
            {"name": "Shortbow", "type": "ranged_attack", "attack_bonus": 4,
             "damage": "1d6+2", "damage_type": "piercing", "range": "80/320"},
        ],
        immunities=["poison"],
        cond_immunities=["exhaustion", "poisoned"],
        description="An animated skeleton, its empty eye sockets faintly glowing.",
    ).to_dict(),

    # ------------------------------------------------------------------ CR 1/2
    "hobgoblin": _make(
        "Hobgoblin", hp=11, ac=18, speed=30, cr=0.5, xp=100,
        str_=13, dex=12, con=12, int_=10, wis=10, cha=9,
        actions=[
            {"name": "Longsword", "type": "melee_attack", "attack_bonus": 3,
             "damage": "1d8+1", "damage_type": "slashing", "reach": 5},
            {"name": "Longbow", "type": "ranged_attack", "attack_bonus": 3,
             "damage": "1d8+1", "damage_type": "piercing", "range": "150/600"},
        ],
        description="A large, militaristic goblinoid with orange skin and a disciplined bearing.",
    ).to_dict(),

    "wolf": _make(
        "Wolf", hp=11, ac=13, speed=40, cr=0.25, xp=50,
        str_=12, dex=15, con=12, int_=3, wis=12, cha=6,
        actions=[
            {"name": "Bite", "type": "melee_attack", "attack_bonus": 4,
             "damage": "2d4+2", "damage_type": "piercing", "reach": 5,
             "on_hit": "DC 11 STR save or knocked prone"},
        ],
        description="A predatory wolf with sharp fangs and a low, threatening growl.",
    ).to_dict(),

    "zombie": _make(
        "Zombie", hp=22, ac=8, speed=20, cr=0.25, xp=50,
        str_=13, dex=6, con=16, int_=3, wis=6, cha=5,
        actions=[
            {"name": "Slam", "type": "melee_attack", "attack_bonus": 3,
             "damage": "1d6+1", "damage_type": "bludgeoning", "reach": 5},
        ],
        immunities=["poison"],
        cond_immunities=["poisoned"],
        description="A shambling undead, rotting flesh barely clinging to its bones.",
    ).to_dict(),

    # ------------------------------------------------------------------ CR 1
    "bugbear": _make(
        "Bugbear", hp=27, ac=16, speed=30, cr=1, xp=200,
        str_=15, dex=14, con=13, int_=8, wis=11, cha=9,
        actions=[
            {"name": "Morningstar", "type": "melee_attack", "attack_bonus": 4,
             "damage": "2d8+2", "damage_type": "piercing", "reach": 5},
            {"name": "Javelin", "type": "ranged_attack", "attack_bonus": 4,
             "damage": "2d6+2", "damage_type": "piercing", "range": "30/120"},
        ],
        senses={"darkvision": 60},
        description="A hulking, hairy goblinoid with a brutal strength and a taste for ambush.",
    ).to_dict(),

    "nothic": _make(
        "Nothic", hp=45, ac=15, speed=30, cr=2, xp=450,
        str_=14, dex=16, con=16, int_=13, wis=10, cha=8,
        actions=[
            {"name": "Multiattack", "type": "multiattack", "attacks": 2},
            {"name": "Rotting Gaze", "type": "special", "attack_bonus": None,
             "range": "30 ft", "effect": "DC 12 CON save or 10 (3d6) necrotic damage"},
            {"name": "Claw", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d6+3", "damage_type": "slashing", "reach": 5},
        ],
        senses={"truesight": 120},
        description="A hunched, one-eyed aberration with a penetrating, unsettling gaze.",
    ).to_dict(),

    # ------------------------------------------------------------------ CR 2
    "ochre_jelly": _make(
        "Ochre Jelly", hp=45, ac=8, speed=10, cr=2, xp=450,
        str_=15, dex=6, con=14, int_=2, wis=6, cha=1,
        actions=[
            {"name": "Pseudopod", "type": "melee_attack", "attack_bonus": 4,
             "damage": "2d6+2", "damage_type": "bludgeoning", "reach": 5,
             "on_hit": "+1d6 acid damage"},
        ],
        resistances=["acid", "fire"],
        immunities=["lightning", "slashing"],
        cond_immunities=["blinded", "charmed", "deafened", "exhaustion", "frightened", "prone"],
        description="An amorphous blob of ochre-colored ooze that dissolves organic matter.",
    ).to_dict(),

    # ------------------------------------------------------------------ LMoP specific
    "grick": _make(
        "Grick", hp=27, ac=14, speed=30, cr=2, xp=450,
        str_=14, dex=14, con=11, int_=3, wis=14, cha=5,
        actions=[
            {"name": "Multiattack", "type": "multiattack", "attacks": 2},
            {"name": "Tentacles", "type": "melee_attack", "attack_bonus": 4,
             "damage": "2d6+2", "damage_type": "slashing", "reach": 5},
            {"name": "Beak", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d6+2", "damage_type": "piercing", "reach": 5},
        ],
        resistances=["bludgeoning", "piercing", "slashing"],
        senses={"darkvision": 60},
        description="A worm-like creature with four tentacles surrounding a razor-sharp beak.",
    ).to_dict(),

    "stirge": _make(
        "Stirge", hp=2, ac=14, speed=10, cr=0.125, xp=25,
        str_=4, dex=16, con=11, int_=2, wis=8, cha=6,
        actions=[
            {"name": "Blood Drain", "type": "melee_attack", "attack_bonus": 5,
             "damage": "1d4+3", "damage_type": "piercing", "reach": 5,
             "on_hit": "attaches and drains 1d4+3 hit points at start of each turn"},
        ],
        senses={"darkvision": 60},
        description="A small, bat-winged creature with a needle-like proboscis that drains blood.",
    ).to_dict(),

    "flameskull": _make(
        "Flameskull", hp=40, ac=13, speed=0, cr=4, xp=1100,
        str_=1, dex=17, con=14, int_=16, wis=10, cha=11,
        actions=[
            {"name": "Multiattack", "type": "multiattack", "attacks": 2},
            {"name": "Fire Ray", "type": "ranged_spell_attack", "attack_bonus": 5,
             "damage": "3d6", "damage_type": "fire", "range": "30 ft"},
            {"name": "Fireball (3/day)", "type": "spell", "save": "DC 13 DEX",
             "damage": "8d6", "damage_type": "fire", "area": "20 ft sphere"},
        ],
        immunities=["fire", "poison", "bludgeoning", "piercing", "slashing"],
        cond_immunities=["charmed", "frightened", "paralyzed", "poisoned", "prone"],
        senses={"darkvision": 60},
        description="A flaming skull that hurls fire and cackles with arcane madness.",
    ).to_dict(),

    # ------------------------------------------------------------------ Bosses
    "klarg": _make(
        "Klarg the Bugbear Chief", hp=27, ac=16, speed=30, cr=1, xp=200,
        str_=15, dex=14, con=13, int_=8, wis=11, cha=9,
        actions=[
            {"name": "Morningstar", "type": "melee_attack", "attack_bonus": 4,
             "damage": "2d8+2", "damage_type": "piercing", "reach": 5},
            {"name": "Javelin", "type": "ranged_attack", "attack_bonus": 4,
             "damage": "2d6+2", "damage_type": "piercing", "range": "30/120"},
        ],
        senses={"darkvision": 60},
        description="A massive bugbear who leads the Cragmaw goblins. Cruel and cunning.",
        monster_id="klarg",
    ).to_dict(),

    "king_grol": _make(
        "King Grol", hp=24, ac=15, speed=30, cr=2, xp=450,
        str_=16, dex=12, con=13, int_=10, wis=9, cha=9,
        actions=[
            {"name": "Multiattack", "type": "multiattack", "attacks": 2},
            {"name": "Battleaxe", "type": "melee_attack", "attack_bonus": 5,
             "damage": "1d8+3", "damage_type": "slashing", "reach": 5},
        ],
        senses={"darkvision": 60},
        description="The aging bugbear chief of Cragmaw Castle. Commands with an iron fist.",
        monster_id="king_grol",
    ).to_dict(),

    "glasstaff": _make(
        "Glasstaff the Wizard", hp=22, ac=12, speed=30, cr=2, xp=450,
        str_=9, dex=14, con=11, int_=17, wis=12, cha=11,
        actions=[
            {"name": "Quarterstaff", "type": "melee_attack", "attack_bonus": 1,
             "damage": "1d6-1", "damage_type": "bludgeoning", "reach": 5},
            {"name": "Spells", "type": "spellcasting",
             "spell_dc": 13, "spell_attack_bonus": 5,
             "spells": ["fire bolt", "mage armor", "magic missile", "shield", "thunderwave"]},
        ],
        description="Iarno Albrek, a treacherous wizard who leads the Redbrands. Wears a glass staff.",
        monster_id="glasstaff",
    ).to_dict(),

    "black_spider": _make(
        "The Black Spider", hp=27, ac=12, speed=30, cr=3, xp=700,
        str_=9, dex=14, con=11, int_=17, wis=13, cha=12,
        actions=[
            {"name": "Dagger", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d4+2", "damage_type": "piercing", "reach": 5},
            {"name": "Web (recharge 5-6)", "type": "ranged_attack", "attack_bonus": 4,
             "damage": "0", "range": "30/60",
             "on_hit": "DC 12 STR save or restrained"},
            {"name": "Spells", "type": "spellcasting",
             "spell_dc": 13, "spell_attack_bonus": 5,
             "spells": ["spider climb", "web", "invisibility", "conjure animals (spiders)"]},
        ],
        senses={"darkvision": 60},
        description="Nezznar, a drow mage obsessed with finding the Forge of Spells. The campaign's villain.",
        monster_id="black_spider",
    ).to_dict(),

    "redbrand_ruffian": _make(
        "Redbrand Ruffian", hp=16, ac=14, speed=30, cr=0.5, xp=100,
        str_=14, dex=13, con=12, int_=9, wis=9, cha=7,
        actions=[
            {"name": "Multiattack", "type": "multiattack", "attacks": 2},
            {"name": "Longsword", "type": "melee_attack", "attack_bonus": 4,
             "damage": "1d8+2", "damage_type": "slashing", "reach": 5},
            {"name": "Heavy Crossbow", "type": "ranged_attack", "attack_bonus": 3,
             "damage": "1d10+1", "damage_type": "piercing", "range": "100/400"},
        ],
        description="A thuggish mercenary wearing a dirty red cloak.",
    ).to_dict(),

    "giant_spider": _make(
        "Giant Spider", hp=26, ac=14, speed=30, cr=1, xp=200,
        str_=14, dex=16, con=12, int_=2, wis=11, cha=4,
        actions=[
            {"name": "Bite", "type": "melee_attack", "attack_bonus": 5,
             "damage": "1d8+3", "damage_type": "piercing", "reach": 5,
             "on_hit": "DC 11 CON save or 2d8 poison damage (half on save)"},
            {"name": "Web (recharge 5-6)", "type": "ranged_attack", "attack_bonus": 5,
             "damage": "0", "range": "30/60",
             "on_hit": "DC 12 STR save or restrained"},
        ],
        senses={"darkvision": 60, "blindsight": 10},
        description="A massive spider the size of a horse, lurking in webs.",
    ).to_dict(),

    "wraith": _make(
        "Wraith", hp=67, ac=13, speed=0, cr=5, xp=1800,
        str_=6, dex=16, con=16, int_=12, wis=14, cha=15,
        actions=[
            {"name": "Life Drain", "type": "melee_attack", "attack_bonus": 6,
             "damage": "4d8+3", "damage_type": "necrotic", "reach": 5,
             "on_hit": "HP max reduced by damage dealt until long rest"},
        ],
        resistances=["acid", "fire", "lightning", "thunder", "bludgeoning", "piercing", "slashing"],
        immunities=["cold", "necrotic", "poison"],
        cond_immunities=["charmed", "exhaustion", "grappled", "paralyzed", "petrified",
                         "poisoned", "prone", "restrained"],
        senses={"darkvision": 60},
        description="A spectral undead that saps life with a chilling touch.",
    ).to_dict(),
}


def get_monster_template(monster_key: str) -> dict | None:
    return MONSTER_TEMPLATES.get(monster_key)


def spawn_monster(monster_key: str, instance_num: int = 1) -> Monster | None:
    template = get_monster_template(monster_key)
    if not template:
        return None
    import copy
    data = copy.deepcopy(template)
    base_id = data["monster_id"] or monster_key
    data["monster_id"] = f"{base_id}_{instance_num}"
    return Monster.from_dict(data)
