"""
Validates player actions against D&D 5e rules and current combat state.
Ensures action economy is respected (1 action, 1 bonus action, 1 movement, 1 reaction per round).
"""
from __future__ import annotations
from data.models import Character, CombatState, CombatantTurn
from engine.combat_engine import get_turn_tracking


class ValidationError(Exception):
    pass


def validate_it_is_your_turn(combat: CombatState, discord_id: str) -> str:
    """Returns the current combatant's ID or raises ValidationError."""
    current_id = combat.current_combatant_id()
    if current_id != discord_id:
        # Check if it's a monster's turn (which happens automatically)
        if current_id and current_id in combat.monsters:
            raise ValidationError("It is the enemy's turn. Please wait.")
        raise ValidationError("It is not your turn yet.")
    return current_id


def validate_action_available(turn: CombatantTurn, action_type: str):
    """Raises ValidationError if the action type has already been used this turn."""
    if action_type == "action" and turn.action_used:
        raise ValidationError(
            "You have already used your **Action** this turn. "
            "You may still use a Bonus Action or move."
        )
    if action_type == "bonus_action" and turn.bonus_action_used:
        raise ValidationError(
            "You have already used your **Bonus Action** this turn."
        )
    if action_type == "reaction" and turn.reaction_used:
        raise ValidationError(
            "You have already used your **Reaction** this turn."
        )


def validate_movement(char: Character, turn: CombatantTurn, feet: int):
    """Raises ValidationError if the character doesn't have enough movement."""
    available = char.speed - turn.movement_used
    if feet > available:
        raise ValidationError(
            f"Not enough movement. You have {available} feet remaining (speed: {char.speed})."
        )


def validate_spell_slot(char: Character, spell_level: int):
    """Raises ValidationError if the character has no available spell slots."""
    if spell_level == 0:
        return  # cantrips don't use slots
    if char.spell_slots.available(spell_level) <= 0:
        raise ValidationError(
            f"You have no available level {spell_level} spell slots."
        )


def validate_spell_known(char: Character, spell_name: str) -> bool:
    """Returns True if the spell is prepared/known, False if not."""
    name_lower = spell_name.lower()
    all_spells = [s.lower() for s in (char.cantrips + char.prepared_spells + char.known_spells)]
    return name_lower in all_spells


def validate_target(combat: CombatState, target_name: str) -> tuple[str, str]:
    """
    Find a target by name (case-insensitive partial match).
    Returns (target_id, target_type) where target_type is 'player' or 'monster'.
    Raises ValidationError if not found.
    """
    target_lower = target_name.lower()

    # Check players
    for pid, pdata in combat.players.items():
        from data.models import Character
        char = Character.from_dict(pdata)
        if target_lower in char.name.lower():
            return pid, "player"

    # Check monsters
    for mid, mdata in combat.monsters.items():
        from data.models import Monster
        mon = Monster.from_dict(mdata)
        if mon.is_alive() and (target_lower in mon.name.lower() or target_lower in mid.lower()):
            return mid, "monster"

    raise ValidationError(
        f"No target named '{target_name}' found in this encounter. "
        "Use `/combat status` to see all combatants."
    )


def consume_action(combat: CombatState, combatant_id: str, action_type: str):
    """Mark an action type as used for the current turn."""
    turn = get_turn_tracking(combat, combatant_id)
    if action_type == "action":
        turn.action_used = True
    elif action_type == "bonus_action":
        turn.bonus_action_used = True
    elif action_type == "reaction":
        turn.reaction_used = True
    from engine.combat_engine import save_turn_tracking
    save_turn_tracking(combat, combatant_id, turn)


def consume_movement(combat: CombatState, combatant_id: str, feet: int):
    """Deduct movement used."""
    turn = get_turn_tracking(combat, combatant_id)
    turn.movement_used += feet
    from engine.combat_engine import save_turn_tracking
    save_turn_tracking(combat, combatant_id, turn)


def get_available_actions_text(char: Character, turn: CombatantTurn) -> str:
    """Return a human-readable summary of what actions are still available."""
    lines = []
    lines.append(f"**{char.name}'s available actions:**")
    lines.append(f"  Action: {'~~Used~~' if turn.action_used else '**Available**'}")
    lines.append(f"  Bonus Action: {'~~Used~~' if turn.bonus_action_used else '**Available**'}")
    movement_left = char.speed - turn.movement_used
    lines.append(f"  Movement: **{movement_left}/{char.speed} ft** remaining")
    lines.append(f"  Reaction: {'~~Used~~' if turn.reaction_used else '**Available** (until next turn)'}")

    if char.spell_slots.slots:
        lines.append("")
        lines.append("  **Spell Slots:**")
        for level in sorted(char.spell_slots.slots.keys()):
            avail = char.spell_slots.available(level)
            total = char.spell_slots.slots[level]
            lines.append(f"    Level {level}: {avail}/{total}")

    return "\n".join(lines)
