"""
D&D 5e combat engine.

Handles the full combat loop:
  - Initiative rolling and ordering
  - Turn structure (action / bonus action / movement / reaction)
  - Attack rolls, damage, saving throws
  - Spell casting
  - Condition tracking
  - Death saves
  - End-of-combat resolution
"""
from __future__ import annotations
import uuid
from typing import Optional

from data.models import Character, Monster, CombatState, CombatantTurn
from data.campaign.monsters import spawn_monster
from data.campaign.spells import get_spell
from engine.dice import (
    roll_d20, roll_dice, roll_with_advantage, roll_with_disadvantage,
    roll_die, format_roll,
)
from engine.rules import ability_modifier, is_crit, is_fumble, CONDITIONS


# ---------------------------------------------------------------------------
# Initiative
# ---------------------------------------------------------------------------

def roll_initiative(characters: list[Character], monsters: list[Monster]) -> CombatState:
    """Roll initiative for all combatants and build a fresh CombatState."""
    encounter_id = str(uuid.uuid4())[:8]
    combat = CombatState(encounter_id=encounter_id)
    combat.is_active = True

    rolls: dict[str, int] = {}

    for char in characters:
        init = roll_d20() + char.ability_scores.dex_mod
        rolls[char.discord_id] = init
        combat.players[char.discord_id] = char.to_dict()

    for monster in monsters:
        init = roll_d20() + ability_modifier(monster.ability_scores.dexterity)
        rolls[monster.monster_id] = init
        combat.monsters[monster.monster_id] = monster.to_dict()

    # Sort by initiative, break ties by DEX (higher is better)
    order = sorted(rolls.keys(), key=lambda cid: rolls[cid], reverse=True)
    combat.initiative_order = order
    combat.initiative_rolls = rolls

    # Initialize turn tracking for every combatant
    for cid in order:
        combat.turn_tracking[cid] = CombatantTurn().to_dict()

    return combat


# ---------------------------------------------------------------------------
# Helpers to get combatant from CombatState
# ---------------------------------------------------------------------------

def get_character_from_combat(combat: CombatState, discord_id: str) -> Optional[Character]:
    data = combat.players.get(discord_id)
    return Character.from_dict(data) if data else None


def get_monster_from_combat(combat: CombatState, monster_id: str) -> Optional[Monster]:
    data = combat.monsters.get(monster_id)
    return Monster.from_dict(data) if data else None


def save_character_to_combat(combat: CombatState, char: Character):
    combat.players[char.discord_id] = char.to_dict()


def save_monster_to_combat(combat: CombatState, monster: Monster):
    combat.monsters[monster.monster_id] = monster.to_dict()


def get_turn_tracking(combat: CombatState, combatant_id: str) -> CombatantTurn:
    data = combat.turn_tracking.get(combatant_id, {})
    return CombatantTurn.from_dict(data)


def save_turn_tracking(combat: CombatState, combatant_id: str, turn: CombatantTurn):
    combat.turn_tracking[combatant_id] = turn.to_dict()


# ---------------------------------------------------------------------------
# Attack resolution
# ---------------------------------------------------------------------------

class ActionResult:
    def __init__(self):
        self.success: bool = False
        self.description: str = ""
        self.damage_dealt: int = 0
        self.healing_done: int = 0
        self.error: str = ""
        self.events: list[str] = []    # significant events (death, condition, etc.)

    def __str__(self):
        return self.description


def resolve_melee_attack(
    attacker_name: str, attack_bonus: int, damage_notation: str, damage_type: str,
    target: Character | Monster, advantage: bool = False, disadvantage: bool = False,
) -> ActionResult:
    result = ActionResult()

    # Roll attack
    if advantage:
        attack_roll, r1, r2 = roll_with_advantage()
        roll_desc = f"d20 [{r1}, {r2}] advantage → {attack_roll}"
    elif disadvantage:
        attack_roll, r1, r2 = roll_with_disadvantage()
        roll_desc = f"d20 [{r1}, {r2}] disadvantage → {attack_roll}"
    else:
        attack_roll = roll_d20()
        roll_desc = f"d20 → {attack_roll}"

    crit = is_crit(attack_roll)
    fumble = is_fumble(attack_roll)
    total_attack = attack_roll + attack_bonus

    target_ac = target.armor_class
    target_name = target.name if isinstance(target, Monster) else target.name

    if fumble:
        result.success = False
        result.description = (
            f"**{attacker_name}** attacks **{target_name}** ({roll_desc} + {attack_bonus} = {total_attack} vs AC {target_ac}) — "
            f"**Critical Miss!** The attack goes wide."
        )
        return result

    hit = crit or (total_attack >= target_ac)

    if hit:
        damage_total, damage_rolls = roll_dice(damage_notation)
        if crit:
            # Double the dice on a crit
            bonus_total, bonus_rolls = roll_dice(damage_notation)
            damage_total += bonus_total
            damage_rolls += bonus_rolls

        outcome = target.take_damage(damage_total, damage_type)
        result.success = True
        result.damage_dealt = damage_total
        crit_text = " **CRITICAL HIT!**" if crit else ""
        result.description = (
            f"**{attacker_name}** attacks **{target_name}** ({roll_desc} + {attack_bonus} = {total_attack} vs AC {target_ac}) — "
            f"**HIT!**{crit_text} {damage_total} {damage_type} damage. {target_name} {outcome}."
        )
        if not target.is_alive():
            result.events.append(f"{target_name}_defeated")
    else:
        result.success = False
        result.description = (
            f"**{attacker_name}** attacks **{target_name}** ({roll_desc} + {attack_bonus} = {total_attack} vs AC {target_ac}) — **MISS!**"
        )

    return result


def resolve_ranged_attack(
    attacker_name: str, attack_bonus: int, damage_notation: str, damage_type: str,
    target: Character | Monster, advantage: bool = False, disadvantage: bool = False,
) -> ActionResult:
    # Same resolution as melee for now
    return resolve_melee_attack(
        attacker_name, attack_bonus, damage_notation, damage_type, target, advantage, disadvantage
    )


def resolve_saving_throw(
    target: Character | Monster, ability: str, dc: int,
    damage_notation: str, damage_type: str, half_on_save: bool = True,
) -> ActionResult:
    result = ActionResult()
    target_name = target.name

    # Get target's ability modifier
    ab = getattr(target.ability_scores, f"{ability[:3]}_mod", 0)
    save_roll = roll_d20()
    total_save = save_roll + ab

    damage_total, _ = roll_dice(damage_notation)

    if total_save >= dc:
        if half_on_save:
            damage_total = damage_total // 2
            outcome = target.take_damage(damage_total, damage_type) if damage_total > 0 else "takes no damage"
            result.description = (
                f"**{target_name}** saves! ({ability.upper()} save: {save_roll} + {ab} = {total_save} vs DC {dc}) — "
                f"{damage_total} {damage_type} damage (half). {target_name} {outcome}."
            )
        else:
            result.description = (
                f"**{target_name}** saves! ({ability.upper()} save: {save_roll} + {ab} = {total_save} vs DC {dc}) — No effect."
            )
        result.damage_dealt = damage_total
    else:
        outcome = target.take_damage(damage_total, damage_type)
        result.success = True
        result.damage_dealt = damage_total
        result.description = (
            f"**{target_name}** fails! ({ability.upper()} save: {save_roll} + {ab} = {total_save} vs DC {dc}) — "
            f"{damage_total} {damage_type} damage. {target_name} {outcome}."
        )

    if not target.is_alive():
        result.events.append(f"{target_name}_defeated")

    return result


# ---------------------------------------------------------------------------
# Spell resolution
# ---------------------------------------------------------------------------

def resolve_spell(
    caster: Character, spell_name: str, spell_slot_level: int,
    target: Character | Monster | None, combat: CombatState,
) -> ActionResult:
    result = ActionResult()
    spell = get_spell(spell_name.lower())

    if not spell:
        result.error = f"Unknown spell: {spell_name}"
        result.description = result.error
        return result

    # Check spell slot
    if spell["level"] > 0:
        if not caster.spell_slots.expend(spell_slot_level):
            result.error = f"No available spell slots at level {spell_slot_level}."
            result.description = result.error
            return result

    # Determine action type consumed
    action_type = spell.get("action_type", "action")

    attack_type = spell.get("attack_type", "")
    damage_notation = spell.get("damage", "")
    damage_type = spell.get("damage_type", "")
    save_ability = spell.get("save")
    save_dc = caster.spell_save_dc()
    spell_attack_bonus = caster.spell_attack_bonus()
    spell_level_name = spell["name"]

    if damage_type == "healing":
        # Healing spell
        if not target:
            result.error = "No target for healing spell."
            return result
        heal_total, _ = roll_dice(damage_notation)
        # Add spellcasting modifier
        heal_total += getattr(caster.ability_scores, f"{caster.spell_ability[:3]}_mod", 0)
        if isinstance(target, Character):
            actual_healed = target.heal(heal_total)
            result.healing_done = actual_healed
            result.success = True
            result.description = (
                f"**{caster.name}** casts **{spell_level_name}**! "
                f"**{target.name}** regains {actual_healed} HP ({target.current_hp}/{target.max_hp} HP)."
            )
        else:
            result.error = "Can't heal monsters."
            return result

    elif attack_type == "ranged_spell" and target:
        result = resolve_ranged_attack(
            caster.name, spell_attack_bonus, damage_notation, damage_type, target
        )
        result.description = f"**{caster.name}** casts **{spell_level_name}**! " + result.description

    elif attack_type == "save" and target and damage_notation:
        result = resolve_saving_throw(
            target, save_ability or "dexterity", save_dc, damage_notation, damage_type
        )
        result.description = f"**{caster.name}** casts **{spell_level_name}**! " + result.description

    elif attack_type == "auto_hit" and target:
        # Magic missile etc.
        darts = spell.get("darts", 1)
        total_damage = 0
        all_rolls = []
        for _ in range(darts):
            dmg, rolls = roll_dice(damage_notation)
            total_damage += dmg
            all_rolls.extend(rolls)
        outcome = target.take_damage(total_damage, damage_type)
        result.success = True
        result.damage_dealt = total_damage
        result.description = (
            f"**{caster.name}** casts **{spell_level_name}**! {darts} dart(s) automatically strike "
            f"**{target.name}** for {total_damage} {damage_type} damage. {target.name} {outcome}."
        )
        if not target.is_alive():
            result.events.append(f"{target.name}_defeated")

    elif attack_type == "buff":
        result.success = True
        result.description = f"**{caster.name}** casts **{spell_level_name}**! {spell['description']}"

    elif attack_type == "utility":
        result.success = True
        result.description = f"**{caster.name}** casts **{spell_level_name}**! {spell['description']}"

    elif attack_type == "movement":
        result.success = True
        result.description = f"**{caster.name}** casts **{spell_level_name}**! {spell['description']}"

    else:
        result.success = True
        result.description = (
            f"**{caster.name}** casts **{spell_level_name}**! {spell['description']}"
        )

    result.success = result.error == ""
    return result


# ---------------------------------------------------------------------------
# Death saves
# ---------------------------------------------------------------------------

def make_death_save(character: Character) -> ActionResult:
    result = ActionResult()
    roll = roll_d20()

    if roll == 20:
        # Miraculous recovery
        character.current_hp = 1
        character.death_saves = {"successes": 0, "failures": 0}
        result.success = True
        result.description = f"**{character.name}** rolls a natural 20! They miraculously regain 1 HP!"
        result.events.append("stabilized")
    elif roll >= 10:
        character.death_saves["successes"] += 1
        successes = character.death_saves["successes"]
        if successes >= 3:
            character.death_saves = {"successes": 0, "failures": 0}
            character.current_hp = 0
            result.description = (
                f"**{character.name}** rolls {roll} — Success! ({successes}/3 successes) "
                f"— **Stabilized!**"
            )
            result.events.append("stabilized")
        else:
            result.description = (
                f"**{character.name}** rolls {roll} — Success ({successes}/3 successes)."
            )
    else:
        character.death_saves["failures"] += 1
        failures = character.death_saves["failures"]
        if failures >= 3:
            result.description = (
                f"**{character.name}** rolls {roll} — **FAILURE** ({failures}/3) — **DEAD!**"
            )
            result.events.append("dead")
        elif roll == 1:
            # Critical failure = 2 failures
            character.death_saves["failures"] += 1
            failures = character.death_saves["failures"]
            result.description = (
                f"**{character.name}** rolls a natural 1! Two failures! ({failures}/3 failures)."
            )
            if failures >= 3:
                result.events.append("dead")
        else:
            result.description = (
                f"**{character.name}** rolls {roll} — Failure ({failures}/3 failures)."
            )

    return result


# ---------------------------------------------------------------------------
# Monster AI — simple but sensible
# ---------------------------------------------------------------------------

def resolve_monster_turn(combat: CombatState, monster_id: str) -> list[ActionResult]:
    """Execute a monster's turn. Returns list of action results."""
    monster = get_monster_from_combat(combat, monster_id)
    if not monster or not monster.is_alive():
        return []

    results = []

    # Find living player targets
    living_players = [
        Character.from_dict(p) for p in combat.players.values()
        if Character.from_dict(p).is_alive()
    ]
    if not living_players:
        return []

    # Simple AI: attack nearest (first in list)
    target = living_players[0]

    # Check for multiattack
    actions = monster.actions or []
    multiattack = next((a for a in actions if a.get("type") == "multiattack"), None)
    attack_actions = [a for a in actions if a.get("type") in ("melee_attack", "ranged_attack")]

    if multiattack and attack_actions:
        num_attacks = multiattack.get("attacks", 2)
        for i in range(num_attacks):
            if not target.is_alive():
                # Try next living player
                living_players = [
                    Character.from_dict(p) for p in combat.players.values()
                    if Character.from_dict(p).is_alive()
                ]
                if not living_players:
                    break
                target = living_players[0]
            attack = attack_actions[i % len(attack_actions)]
            result = resolve_melee_attack(
                monster.name,
                attack.get("attack_bonus", 0),
                attack.get("damage", "1d6"),
                attack.get("damage_type", "bludgeoning"),
                target,
            )
            # Save updated target back
            save_character_to_combat(combat, target)
            results.append(result)

    elif attack_actions:
        attack = attack_actions[0]
        result = resolve_melee_attack(
            monster.name,
            attack.get("attack_bonus", 0),
            attack.get("damage", "1d6"),
            attack.get("damage_type", "bludgeoning"),
            target,
        )
        save_character_to_combat(combat, target)
        results.append(result)

    else:
        ar = ActionResult()
        ar.description = f"**{monster.name}** glares menacingly but takes no action."
        results.append(ar)

    return results


# ---------------------------------------------------------------------------
# Combat flow
# ---------------------------------------------------------------------------

def start_encounter(
    encounter_key: str,
    characters: list[Character],
    encounter_data: dict,
) -> tuple[CombatState, str]:
    """
    Spawn monsters from encounter data, roll initiative, return CombatState
    and an initiative order string.
    """
    from data.campaign.monsters import spawn_monster

    monsters = []
    monster_counts: dict[str, int] = {}
    for entry in encounter_data.get("monsters", []):
        key = entry["key"]
        count = entry.get("count", 1)
        for i in range(count):
            monster_counts[key] = monster_counts.get(key, 0) + 1
            m = spawn_monster(key, monster_counts[key])
            if m:
                monsters.append(m)

    combat = roll_initiative(characters, monsters)
    combat.encounter_name = encounter_data.get("name", "Encounter")
    combat.location = encounter_data.get("location", "")

    # Build initiative order string
    order_lines = []
    for cid in combat.initiative_order:
        roll = combat.initiative_rolls[cid]
        if cid in combat.players:
            char = Character.from_dict(combat.players[cid])
            order_lines.append(f"**{char.name}** (Player) — Initiative {roll}")
        elif cid in combat.monsters:
            mon = Monster.from_dict(combat.monsters[cid])
            order_lines.append(f"**{mon.name}** (Enemy) — Initiative {roll}")

    order_str = "\n".join(f"{i+1}. {line}" for i, line in enumerate(order_lines))
    combat.add_log(f"Combat begins: {combat.encounter_name}")

    return combat, order_str


def is_combat_over(combat: CombatState) -> tuple[bool, str]:
    """Check if combat is over. Returns (is_over, reason)."""
    all_monsters_dead = all(
        not Monster.from_dict(m).is_alive() for m in combat.monsters.values()
    )
    all_players_dead = all(
        not Character.from_dict(p).is_alive() for p in combat.players.values()
    )

    if all_monsters_dead:
        return True, "victory"
    if all_players_dead:
        return True, "defeat"
    return False, ""


def get_combat_status(combat: CombatState) -> str:
    """Return a formatted status string for the current combat state."""
    lines = [f"**Round {combat.round_number}** — {combat.encounter_name}", ""]

    lines.append("**Players:**")
    for pid, pdata in combat.players.items():
        char = Character.from_dict(pdata)
        hp_bar = _hp_bar(char.current_hp, char.max_hp)
        status = ", ".join(char.conditions) if char.conditions else "healthy"
        lines.append(f"  {char.name}: {hp_bar} ({char.current_hp}/{char.max_hp} HP) — {status}")

    lines.append("")
    lines.append("**Enemies:**")
    for mid, mdata in combat.monsters.items():
        mon = Monster.from_dict(mdata)
        if mon.is_alive():
            hp_bar = _hp_bar(mon.current_hp, mon.max_hp)
            lines.append(f"  {mon.name}: {hp_bar} ({mon.current_hp}/{mon.max_hp} HP)")
        else:
            lines.append(f"  ~~{mon.name}~~ — **Defeated**")

    # Current turn
    current_id = combat.current_combatant_id()
    if current_id:
        if current_id in combat.players:
            current_name = Character.from_dict(combat.players[current_id]).name
        elif current_id in combat.monsters:
            current_name = Monster.from_dict(combat.monsters[current_id]).name
        else:
            current_name = "Unknown"
        lines.append(f"\n**Current Turn:** {current_name}")

    return "\n".join(lines)


def _hp_bar(current: int, maximum: int, length: int = 10) -> str:
    if maximum == 0:
        return "░" * length
    filled = round((current / maximum) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"`[{bar}]`"
