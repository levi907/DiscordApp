"""
Action parser — uses Claude to interpret natural language player descriptions
and convert them into structured game actions.
"""
from __future__ import annotations
import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, AI_MODEL
from ai.narrator import ACTION_PARSER_SYSTEM


def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


async def parse_player_action(
    player_description: str,
    available_spells: list[str],
    available_items: list[str],
    is_rogue: bool = False,
    context: str = "",
) -> dict:
    """
    Parse a player's natural language action description into a structured dict.
    Returns a dict matching the ACTION_PARSER_SYSTEM schema.
    Falls back to a low-confidence 'other' action on parse failure.
    """
    spells_str = ", ".join(available_spells) if available_spells else "none"
    items_str = ", ".join(available_items) if available_items else "none"

    prompt = (
        f"Player says: \"{player_description}\"\n\n"
        f"Available spells: {spells_str}\n"
        f"Available items: {items_str}\n"
        f"Is Rogue (can use Cunning Action for bonus action Hide/Disengage/Dash): {is_rogue}\n"
        f"{'Context: ' + context if context else ''}\n\n"
        "Parse this into a JSON action object."
    )

    client = get_client()
    try:
        message = await client.messages.create(
            model=AI_MODEL,
            max_tokens=300,
            system=ACTION_PARSER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Extract JSON from the response (in case there's surrounding text)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            action = json.loads(json_match.group())
            return action
    except (json.JSONDecodeError, anthropic.APIError, IndexError):
        pass

    # Fallback: try simple keyword matching
    return _fallback_parse(player_description)


def _fallback_parse(text: str) -> dict:
    """Keyword-based fallback parser when AI is unavailable."""
    lower = text.lower()

    action: dict = {
        "action_type": "other",
        "target": None,
        "spell_name": None,
        "spell_slot_level": None,
        "item_name": None,
        "movement_feet": None,
        "description": text,
        "is_bonus_action": False,
        "confidence": "low",
    }

    if "bonus action" in lower:
        action["is_bonus_action"] = True

    if any(w in lower for w in ["attack", "hit", "strike", "slash", "stab", "shoot"]):
        action["action_type"] = "attack"
        action["confidence"] = "medium"

    elif any(w in lower for w in ["cast", "spell", "fire bolt", "magic missile", "cure", "heal",
                                   "sacred flame", "thunderwave", "sleep", "fireball", "shield",
                                   "misty step", "bless", "hold", "burning hands"]):
        action["action_type"] = "spell"
        action["confidence"] = "medium"
        # Try to extract spell name
        spell_keywords = [
            "fire bolt", "magic missile", "cure wounds", "healing word", "sacred flame",
            "thunderwave", "sleep", "fireball", "shield", "misty step", "bless",
            "hold person", "burning hands", "detect magic", "faerie fire", "spiritual weapon",
            "minor illusion", "mage hand", "light", "guidance", "eldritch blast",
            "counterspell",
        ]
        for spell in spell_keywords:
            if spell in lower:
                action["spell_name"] = spell
                action["spell_slot_level"] = 0 if spell in ["fire bolt", "sacred flame",
                    "mage hand", "prestidigitation", "light", "guidance", "thaumaturgy",
                    "eldritch blast", "minor illusion", "toll the dead"] else 1
                break

    elif any(w in lower for w in ["move", "walk", "run", "go to", "advance", "retreat", "step"]):
        action["action_type"] = "move"
        action["confidence"] = "medium"
        # Try to extract distance
        dist_match = re.search(r'(\d+)\s*(?:feet|foot|ft)', lower)
        if dist_match:
            action["movement_feet"] = int(dist_match.group(1))

    elif "dash" in lower:
        action["action_type"] = "dash"
        action["confidence"] = "high"

    elif "dodge" in lower:
        action["action_type"] = "dodge"
        action["confidence"] = "high"

    elif "hide" in lower:
        action["action_type"] = "hide"
        action["confidence"] = "high"

    elif "disengage" in lower:
        action["action_type"] = "disengage"
        action["confidence"] = "high"

    elif "help" in lower:
        action["action_type"] = "help"
        action["confidence"] = "high"

    elif any(w in lower for w in ["potion", "use", "drink", "apply"]):
        action["action_type"] = "item"
        action["confidence"] = "medium"
        if "potion" in lower:
            action["item_name"] = "Potion of Healing"

    # Try to extract target
    target_match = re.search(r'(?:at|on|against|target)\s+(?:the\s+)?([a-zA-Z\s]+?)(?:\s+with|\s+using|$)', lower)
    if target_match:
        action["target"] = target_match.group(1).strip()

    return action
