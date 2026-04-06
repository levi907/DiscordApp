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

If a FORESHADOWING directive is included, you MUST weave subtle environmental clues
toward that threat into your description (tracks, sounds, smells, unnatural silence,
distant shapes, disturbed ground). Never name the threat directly or state that a fight
is coming — hint only through atmosphere and sensory detail.

Campaign context is provided in the user message. Use it to stay consistent.
"""

COMBAT_NARRATOR_SYSTEM = """You are narrating D&D 5e combat using theater of the mind principles.

CRITICAL RULE — ACTION BEFORE OUTCOME:
Every narration must describe the attacker's PHYSICAL ACTION first, then the result.
Show the motion, effort, stance, and intent before revealing what happens to the target.
  ✓ "Mira lunges forward, driving her blade in a tight arc at the goblin's exposed ribs — steel
     grinds against bone and the creature staggers back with a shriek."
  ✗ "Mira hits the goblin for 7 piercing damage."

Additional rules:
- 1-3 sentences per event. Punchy and visceral.
- Include sensory details: sound of steel, flash of fire, splatter of blood, smell of char.
- Misses: describe the near-miss or defensive action, not a blank whiff.
- Crits: amplify the drama — a devastating, decisive blow with lasting imagery.
- Kills: one vivid final sentence describing the creature's demise.
- Never mention dice, HP numbers, or game statistics.
- Keep the initiative flow fast — don't over-describe.
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
    foreshadow_name: str = "",
    foreshadow_hint: str = "",
) -> str:
    """
    Generate a 2-4 sentence scene introduction.

    If foreshadow_name/hint are provided, the AI will weave subtle environmental
    clues toward the upcoming encounter into the description without naming it.
    """
    context = f"Location: {location_name}\nDescription: {location_description}\nChapter: {chapter}"
    if recent_events:
        context += "\nRecent events: " + "; ".join(recent_events[-3:])
    if foreshadow_name and foreshadow_hint:
        context += (
            f"\n\nFORESHADOWING — upcoming threat at this location: {foreshadow_name}.\n"
            f"Context: {foreshadow_hint}\n"
            "Embed 1-2 subtle sensory clues toward this danger in your description "
            "(tracks, sounds, smells, shadows, unnatural silence, distant shapes). "
            "Do NOT name the creature or state that a fight is coming."
        )

    prompt = f"Describe this scene for the players as they arrive.\n\n{context}"

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
        "Narrate this combat moment in 1-3 sentences. "
        "Lead with the attacker's physical motion and technique, then describe the result."
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


async def should_trigger_combat(
    location_name: str,
    location_description: str,
    available_encounter: str,
    encounter_description: str,
    story_flags: dict,
    chapter: int,
) -> tuple[bool, str]:
    """
    Ask the AI whether arriving at this location should immediately trigger combat.
    Returns (should_start, reason_text).
    """
    system = (
        "You are a D&D 5e Dungeon Master deciding whether combat should begin immediately "
        "when the party arrives at a location. Answer with ONLY a JSON object:\n"
        '{"start_combat": true/false, "reason": "one sentence explanation"}\n\n'
        "Start combat if the encounter description implies an ambush, enemies actively "
        "guarding, or any immediate physical threat. Be proactive — if the location is "
        "hostile territory or the enemy would logically notice and attack, start combat. "
        "Do NOT start combat only for locations that are clearly neutral or friendly."
    )
    prompt = (
        f"Location: {location_name}\n"
        f"Description: {location_description}\n"
        f"Possible encounter: {available_encounter}\n"
        f"Encounter description: {encounter_description}\n"
        f"Campaign chapter: {chapter}\n"
        f"Story flags already set: {list(story_flags.keys())}\n\n"
        "Should combat trigger immediately when the party arrives?"
    )

    client = get_client()
    try:
        import json
        message = await client.messages.create(
            model=AI_MODEL,
            max_tokens=100,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return bool(data.get("start_combat", False)), data.get("reason", "")
    except Exception:
        pass
    return False, ""


async def evaluate_combat_trigger(
    trigger_description: str,
    location_name: str,
    available_encounters: dict[str, str],
    story_flags: dict,
    chapter: int,
) -> tuple[bool, str | None, str]:
    """
    Evaluate whether a player action, NPC response, or scene event should trigger combat.
    Checks for violence, hostility, ambushes, threats, blood, and escalating confrontations.

    Returns (should_start, encounter_key_or_None, reason).
    available_encounters: {encounter_key: description}
    """
    if not available_encounters:
        return False, None, ""

    enc_list = "\n".join(f"- {k}: {v}" for k, v in available_encounters.items())
    system = (
        "You are a D&D 5e Dungeon Master deciding whether to immediately start combat "
        "based on a player action or NPC response.\n\n"
        "START COMBAT if you detect ANY of the following:\n"
        "- Player attempts, threatens, or implies violence or an attack\n"
        "- Player draws a weapon in a hostile or tense situation\n"
        "- An NPC becomes very angry, feels threatened, or is betrayed by the players\n"
        "- An NPC or creature attacks or lunges at the party\n"
        "- The scene describes blood, physical confrontation, or weapons clashing\n"
        "- A failed social roll with a hostile NPC tips into violence\n"
        "- The party provokes guards, bandits, monsters, or hostile creatures\n"
        "- An ambush is sprung or the party is caught trespassing by hostile enemies\n"
        "- Any hint that a fight is about to break out right now\n\n"
        "Do NOT start combat for:\n"
        "- Peaceful exploration or conversation\n"
        "- Tense but non-violent situations\n"
        "- Friendly or neutral NPCs\n\n"
        "You MUST output ONLY valid JSON:\n"
        '{"start_combat": true/false, "encounter_key": "<key from list or null>", '
        '"reason": "one sentence"}\n\n'
        "Choose encounter_key from the provided list, or null if no encounter fits."
    )
    prompt = (
        f"Location: {location_name} (Chapter {chapter})\n"
        f"Story flags already completed: {list(story_flags.keys())}\n"
        f"Available encounters:\n{enc_list}\n\n"
        f"Event to evaluate:\n{trigger_description}\n\n"
        "Should this trigger combat? If yes, which encounter?"
    )

    client = get_client()
    try:
        import json, re
        message = await client.messages.create(
            model=AI_MODEL,
            max_tokens=120,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            start   = bool(data.get("start_combat", False))
            enc_key = data.get("encounter_key") or None
            reason  = data.get("reason", "")
            # Validate the key is actually in our available list
            if enc_key and enc_key not in available_encounters:
                enc_key = next(iter(available_encounters))  # fall back to first
            return start, enc_key, reason
    except Exception:
        pass
    return False, None, ""
