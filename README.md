# Lost Mines of Phandelver — D&D Discord Bot

A fully-featured Discord bot that runs the *Lost Mines of Phandelver* D&D 5e campaign with AI narration powered by Claude.

## Features

- **AI Narration**: Claude generates vivid, theater-of-the-mind scene descriptions and combat narration
- **Structured D&D 5e Combat Engine**: Full initiative, action economy (action/bonus action/movement/reaction), attack rolls, saving throws, spell casting
- **Channel System**:
  - `📖narration` — DM narration (read-only for players)
  - `📋game-log` — Quests, combat logs, loot, session summaries
  - `🧙player-name` — Private per-player channels for character management and actions
- **Character Management**: Create characters from LMoP class archetypes with rolled stats, starting equipment, and spells
- **Full Campaign Data**: All LMoP encounters, monsters, locations, NPCs, quests, and items included
- **Natural Language Actions**: Players describe actions in plain English; AI converts them to game mechanics

## Setup

1. **Create a Discord Bot** at the [Discord Developer Portal](https://discord.com/developers/applications)
   - Enable `Message Content Intent` and `Server Members Intent`
   - Invite with permissions: `Manage Channels`, `Send Messages`, `Embed Links`, `Read Message History`

2. **Get an Anthropic API Key** from [console.anthropic.com](https://console.anthropic.com)

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and fill in DISCORD_TOKEN and ANTHROPIC_API_KEY
   ```

5. **Run the bot**:
   ```bash
   python bot.py
   ```

## Command Reference

### Game Management
| Command | Description |
|---------|-------------|
| `/game_start @player1 @player2 ...` | Start campaign, create channels |
| `/game_status` | Campaign overview |
| `/game_location` | Narrate current location |
| `/game_travel <location>` | Move party to a location |
| `/game_npc <name> <message>` | Talk to an NPC (AI responds) |
| `/game_end` | End campaign, delete channels |
| `/quest_list` | View all quests |
| `/log_summary` | View session summaries |
| `/log_combat` | View combat log |
| `/log_loot` | View loot history |

### Character
| Command | Description |
|---------|-------------|
| `/character_create <name> <race> <class>` | Create your character |
| `/character_sheet` | View full character sheet |
| `/character_spells` | View spells and spell slots |
| `/character_inventory` | View inventory |
| `/character_features` | View class features and traits |
| `/character_actions` | Show available actions this turn |
| `/character_rest <short\|long>` | Take a rest |
| `/character_heal @player <amount>` | Heal a player (DM) |

### Combat
| Command | Description |
|---------|-------------|
| `/combat_encounter <name>` | Start a named encounter |
| `/combat_status` | Current combat state |
| `/combat_action <description>` | Declare action in plain English |
| `/combat_attack <target>` | Weapon attack |
| `/combat_cast <spell> [target] [slot]` | Cast a spell |
| `/combat_move <feet>` | Move N feet |
| `/combat_dash` | Dash (double movement, costs action) |
| `/combat_dodge` | Dodge (costs action) |
| `/combat_hide` | Hide (costs action) |
| `/combat_disengage` | Disengage (costs action) |
| `/combat_end_turn` | End your turn |
| `/combat_death_save` | Death saving throw |

## Available Races
Human, Elf, Dwarf, Halfling, Half-Elf, Half-Orc, Gnome, Dragonborn, Tiefling

## Available Classes
Fighter, Wizard, Rogue, Cleric, Ranger, Paladin, Barbarian, Bard, Warlock, Sorcerer, Druid, Monk

## LMoP Encounters Available
- `goblin_ambush` — Chapter 1: Triboar Trail ambush
- `cragmaw_hideout_entry` — Chapter 1: Cave entrance
- `cragmaw_hideout_klarg` — Chapter 1: Klarg's lair (boss)
- `redbrand_hideout` — Chapter 2: Tresendar Manor
- `old_owl_well` — Chapter 3: Zombie horde
- `orc_camp` — Chapter 3: Wyvern Tor
- `wave_echo_cave_black_spider` — Chapter 4: Final boss

## Architecture

```
DiscordApp/
├── bot.py                    # Main entry point
├── config.py                 # Environment configuration
├── requirements.txt
├── cogs/
│   ├── game_cog.py           # Campaign & quest commands
│   ├── character_cog.py      # Character management commands
│   └── combat_cog.py         # Combat commands
├── engine/
│   ├── combat_engine.py      # D&D 5e combat resolution
│   ├── dice.py               # Dice rolling utilities
│   ├── rules.py              # D&D 5e rules constants
│   └── action_validator.py   # Action economy enforcement
├── ai/
│   ├── narrator.py           # Claude AI narration
│   └── action_parser.py      # Natural language → game action
├── data/
│   ├── database.py           # Async SQLite layer
│   ├── models.py             # Dataclasses (Character, Monster, etc.)
│   └── campaign/
│       ├── lmop.py           # LMoP campaign data
│       ├── monsters.py       # Monster stat blocks
│       ├── spells.py         # Spell data
│       └── items.py          # Items and equipment
└── utils/
    ├── embeds.py             # Discord embed builders
    └── permissions.py        # Channel permission utilities
```
