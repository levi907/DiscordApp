"""
AI Narrator — uses Claude to generate vivid, theater-of-the-mind descriptions
for scene introductions, combat narration, and story events.

All descriptions are kept brief (2-4 sentences) and evocative.
"""
from __future__ import annotations
import anthropic
from config import ANTHROPIC_API_KEY, AI_MODEL, AI_MAX_TOKENS


_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

NARRATOR_SYSTEM = """You are the Dungeon Master narrating the D&D 5e adventure "Lost Mines of Phandelver."

Your style:
- Brief and vivid: 2-4 sentences maximum per response.
- Theater of the mind: paint sensory details — what is seen, heard, smelled, felt.
- Second person ("you see...", "before you stands...").
- Dramatic but not overwrought. Grim when appropriate, wondrous when warranted.
- Never break character or mention game mechanics in narration.
- Never summarize what players already know — describe the new moment.

Campaign context is provided in the user message. Use it to stay consistent.
"""

COMBAT_NARRATOR_SYSTEM = """You are narrating D&D 5e combat using theater of the mind principles.

Rules for combat narration:
- 1-3 sentences per combat event. Be punchy and visceral.
- Describe the physical action: "The goblin ducks under your swing and drives a blade at your ribs."
- Include sensory details for hits: the sound of steel on bone, the flash of fire, the splatter of blood.
- For misses: describe the near-miss or defensive action that saved the target.
- For crits: amplify the drama — a devastating, decisive blow.
- For kills: 1 vivid sentence of the creature's demise.
- Never mention dice, HP numbers, or game stats in narration.
- Keep initiative flow fast — don't over-describe.
"""

ACTION_PARSER_SYSTEM = """You are a D&D 5e rules assistant. Convert a player's natural language description
into a structured game action.

Output ONLY a JSON object with these fields:
{
  "action_type": "attack" | "spell" | "move" | "dash" | "dodge" | "help" | "hide" | "disengage" | "item" | "other",
  "target": "target name or null",
  "spell_name": "spell name or null",
  "spell_slot_level": integer or null,
  "item_name": "item name or null",
  "movement_feet": integer or null,
  "description": "brief cleaned-up description of the action",
  "is_bonus_action": boolean,
  "confidence": "high" | "medium" | "low"
}

Rules:
- "attack" means a weapon attack (action).
- "spell" requires spell_name and spell_slot_level (0 for cantrips).
- "move" uses movement. "dash" is an action that doubles movement.
- "dodge" is an action; attacks against the character have disadvantage.
- "help" is an action; one ally gets advantage on next check/attack.
- "hide" is an action or bonus action (Rogue); Stealth check to become hidden.
- "disengage" is an action or bonus action (Rogue); movement doesn't provoke opportunity attacks.
- "item" uses an item (usually an action, potions can be bonus action for some classes).
- If the player says "bonus action" explicitly, set is_bonus_action true.
- If unsure, use confidence "low" and best-guess action_type.
"""


# ---------------------------------------------------------------------------
# Narration functions
# ---------------------------------------------------------------------------

async def narrate_scene(
    location_name: str,
    location_description: str,
    chapter: int,
    recent_events: list[str] | None = None,
) -> str:
    """Generate a 2-4 sentence scene introduction."""
    context = f"Location: {location_name}\nDescription: {location_description}\nChapter: {chapter}"
    if recent_events:
        context += "\nRecent events: " + "; ".join(recent_events[-3:])

    prompt = f"""Describe this scene for the players as they arrive.\n\n{context}"""

    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=256,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def narrate_encounter_start(
    encounter_name: str,
    encounter_description: str,
    monster_names: list[str],
    location: str,
) -> str:
    """Narrate the start of a combat encounter."""
    monsters_str = ", ".join(monster_names)
    prompt = (
        f"An encounter begins: {encounter_name}\n"
        f"Location: {location}\n"
        f"Enemies: {monsters_str}\n"
        f"Description: {encounter_description}\n\n"
        "Narrate the moment combat erupts. Set the scene. End with a call to action."
    )

    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=256,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def narrate_combat_action(
    action_description: str,
    mechanical_result: str,
    context: str = "",
) -> str:
    """
    Convert a mechanical combat result into vivid narration.
    action_description: what the player/monster tried to do
    mechanical_result: what actually happened (hit for 8 slashing, missed, etc.)
    """
    prompt = (
        f"Action: {action_description}\n"
        f"Outcome: {mechanical_result}\n"
        f"{'Context: ' + context if context else ''}\n\n"
        "Narrate this combat moment in 1-3 sentences."
    )

    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=150,
        system=COMBAT_NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def narrate_victory(
    encounter_name: str,
    fallen_enemies: list[str],
    location: str,
    loot: list[dict] | None = None,
) -> str:
    """Narrate a combat victory."""
    enemies_str = ", ".join(fallen_enemies)
    loot_str = ""
    if loot:
        loot_str = "Loot: " + ", ".join(f"{l.get('quantity', 1)}x {l['name']}" for l in loot)

    prompt = (
        f"The party defeats: {enemies_str}\n"
        f"Location: {location}\n"
        f"Encounter: {encounter_name}\n"
        f"{loot_str}\n\n"
        "Narrate the moment victory is achieved. Describe the aftermath. "
        "If there is loot, mention it briefly. 2-3 sentences."
    )

    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=200,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def narrate_defeat() -> str:
    """Narrate a total party kill."""
    prompt = (
        "The party has been defeated — all characters are unconscious or dead. "
        "Narrate the grim ending. 2-3 sentences. Leave a sliver of hope if possible."
    )
    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=150,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def narrate_npc_dialogue(
    npc_name: str,
    npc_description: str,
    player_said: str,
    campaign_context: str = "",
) -> str:
    """Generate NPC dialogue response."""
    system = (
        f"{NARRATOR_SYSTEM}\n\n"
        f"You are voicing {npc_name}: {npc_description}. "
        "Stay in character. Keep dialogue brief (1-3 lines of speech + 1 line of action/description)."
    )
    prompt = (
        f"The player says to {npc_name}: \"{player_said}\"\n"
        f"{'Campaign context: ' + campaign_context if campaign_context else ''}\n\n"
        "Respond as this NPC."
    )
    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def generate_session_summary(
    events: list[str],
    chapter: int,
    location: str,
    player_names: list[str],
) -> str:
    """Generate a brief recap of the session's events for the log channel."""
    events_str = "\n".join(f"- {e}" for e in events)
    prompt = (
        f"Campaign: Lost Mines of Phandelver, Chapter {chapter}\n"
        f"Location: {location}\n"
        f"Players: {', '.join(player_names)}\n"
        f"Events this session:\n{events_str}\n\n"
        "Write a brief (3-5 sentence) 'Previously...' style recap of this session. "
        "Past tense. Third person. Dramatic."
    )
    client = get_client()
    message = await client.messages.create(
        model=AI_MODEL,
        max_tokens=300,
        system=NARRATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
