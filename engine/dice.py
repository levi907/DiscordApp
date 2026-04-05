"""
Dice rolling utilities for D&D 5e.
"""
import random
import re


def roll_die(sides: int) -> int:
    return random.randint(1, sides)


def roll_dice(notation: str) -> tuple[int, list[int]]:
    """
    Parse and roll dice notation like '2d6+3', '1d8-1', '4d6', '1d20'.
    Returns (total, individual_rolls).
    """
    notation = notation.strip().lower()
    pattern = r'^(\d+)d(\d+)([+-]\d+)?$'
    match = re.match(pattern, notation)
    if not match:
        # Try plain number
        try:
            val = int(notation)
            return val, [val]
        except ValueError:
            return 0, []

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    rolls = [roll_die(sides) for _ in range(count)]
    total = sum(rolls) + modifier
    return max(0, total), rolls


def roll_d20() -> int:
    return roll_die(20)


def roll_with_advantage() -> tuple[int, int, int]:
    """Roll 2d20, return (higher, roll1, roll2)."""
    r1, r2 = roll_die(20), roll_die(20)
    return max(r1, r2), r1, r2


def roll_with_disadvantage() -> tuple[int, int, int]:
    """Roll 2d20, return (lower, roll1, roll2)."""
    r1, r2 = roll_die(20), roll_die(20)
    return min(r1, r2), r1, r2


def roll_ability_scores() -> list[int]:
    """Roll 4d6 drop lowest, six times."""
    scores = []
    for _ in range(6):
        rolls = [roll_die(6) for _ in range(4)]
        scores.append(sum(sorted(rolls)[1:]))
    return scores


def format_roll(total: int, rolls: list[int], modifier: int = 0, label: str = "") -> str:
    roll_str = " + ".join(str(r) for r in rolls)
    if len(rolls) > 1 or modifier != 0:
        detail = f"[{roll_str}]"
        if modifier > 0:
            detail += f" + {modifier}"
        elif modifier < 0:
            detail += f" - {abs(modifier)}"
        return f"**{total}** ({label}{detail})" if label else f"**{total}** ({detail})"
    return f"**{total}**"


def check_proficiency_modifier(proficiency_bonus: int, has_expertise: bool = False) -> int:
    return proficiency_bonus * 2 if has_expertise else proficiency_bonus
