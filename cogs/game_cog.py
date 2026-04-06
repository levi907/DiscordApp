"""
Game management cog — starting campaigns, joining, status, and session management.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import data.database as db
from data.models import CampaignState, Quest
from data.campaign.lmop import CHAPTERS, LOCATIONS, STARTING_QUESTS, get_encounter
from ai.narrator import narrate_scene, narrate_encounter_start, generate_session_summary
from utils.embeds import (
    narration_embed, campaign_status_embed, quest_embed, info_embed,
    error_embed, success_embed,
)
from utils.permissions import (
    create_campaign_category, create_narration_channel,
    create_log_channel, create_player_channel, cleanup_campaign_channels,
)
from engine.combat_engine import start_encounter, get_combat_status
from data.campaign.lmop import ENCOUNTERS


HELP_TEXT = """
**🎲 Lost Mines of Phandelver — Command Reference**

**Game Management**
`/game start <players>` — Start a new campaign session (list Discord user mentions)
`/game status` — Show campaign overview
`/game location` — Narrate the current location
`/game travel <location>` — Move the party to a new location
`/game npc <name> <message>` — Talk to an NPC
`/game end` — End the campaign and clean up channels

**Character**
`/character create <name> <race> <class>` — Create your character
`/character sheet` — View your full character sheet
`/character spells` — View your spells and spell slots
`/character inventory` — View your inventory
`/character heal <amount>` — Heal HP (DM use / magic)
`/character rest <short|long>` — Take a short or long rest

**Combat**
`/combat encounter <name>` — Start a named encounter
`/combat status` — Show current combat state
`/combat action <description>` — Declare your action (AI-parsed)
`/combat attack <target>` — Make a weapon attack
`/combat cast <spell> [target] [slot]` — Cast a spell
`/combat move <feet>` — Move (use your movement)
`/combat dash` — Dash (action: double movement)
`/combat dodge` — Dodge (action: attacks vs you have disadvantage)
`/combat hide` — Hide (action or Rogue bonus action)
`/combat disengage` — Disengage (action or Rogue bonus action)
`/combat end_turn` — End your turn
`/combat death_save` — Make a death saving throw

**Quests & Logs**
`/quest list` — Show all active quests
`/quest complete <id>` — Mark a quest objective complete
`/log combat` — Show recent combat log
`/log summary` — Show session summary
`/log loot` — Show loot acquired

**Exploration & Actions**
`/action_look` — Describe the current scene
`/action_examine <target>` — Closely inspect something ("the chest", "the door")
`/action_search` — Search area for hidden things (rolls Perception + Investigation)
`/action_skill <skill> <description> [dc]` — Make any skill check (stealth, persuasion, etc.)
`/action_sneak` — Move stealthily (Stealth check, auto-disadvantage with heavy armor)
`/action_talk <npc> <message>` — Speak to an NPC — AI responds in character
`/action_loot` — Check loot from recent combat
`/action_do <description>` — Describe ANY action — AI acts as DM and narrates the outcome
`/action_conditions [condition]` — Look up a D&D condition (poisoned, prone, etc.)

**Help**
`/help` — Show this message
"""


class GameCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # /help
    # ------------------------------------------------------------------

    @app_commands.command(name="help", description="Show all available commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = info_embed("D&D Bot Commands", HELP_TEXT)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /game start
    # ------------------------------------------------------------------

    @app_commands.command(name="game_start", description="Start a new Lost Mines of Phandelver campaign")
    @app_commands.describe(players="Mention all participating players (e.g. @Alice @Bob @Carol)")
    async def game_start(self, interaction: discord.Interaction, players: str):
        await interaction.response.defer(ephemeral=False)
        try:
            await self._game_start_inner(interaction, players)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                await interaction.followup.send(embed=error_embed(
                    f"Unexpected error starting game:\n```{type(e).__name__}: {e}```\n"
                    f"Check Railway logs for the full traceback."
                ))
            except Exception:
                pass
            raise  # re-raise so it appears in Railway logs

    async def _game_start_inner(self, interaction: discord.Interaction, players: str):
        guild = interaction.guild
        if not guild:
            await interaction.followup.send(embed=error_embed("Must be used in a server."))
            return

        # Check for existing campaign
        existing = await db.load_campaign(str(guild.id))
        if existing:
            await interaction.followup.send(
                embed=error_embed("A campaign is already running! Use `/game_end` first."),
                ephemeral=True,
            )
            return

        # Parse mentioned players — also accept the invoker with no mentions
        player_members: list[discord.Member] = []
        for word in players.split():
            if word.startswith("<@") and word.endswith(">"):
                uid = word.strip("<@!>")
                try:
                    member = guild.get_member(int(uid)) or await guild.fetch_member(int(uid))
                    if member and not member.bot:
                        player_members.append(member)
                except Exception:
                    pass

        # Always include the command invoker
        if interaction.user not in player_members:
            if isinstance(interaction.user, discord.Member):
                player_members.append(interaction.user)

        player_ids = [str(m.id) for m in player_members]

        # Create Discord channels
        try:
            category = await create_campaign_category(guild, "Lost Mines of Phandelver")
            narration_ch = await create_narration_channel(guild, category, player_ids, None)
            log_ch = await create_log_channel(guild, category, player_ids, None)

            player_channel_ids: dict[str, str] = {}
            for member in player_members:
                ch = await create_player_channel(guild, category, member, None)
                player_channel_ids[str(member.id)] = str(ch.id)
        except discord.Forbidden as e:
            await interaction.followup.send(embed=error_embed(
                f"Missing permissions to create channels.\n"
                f"Discord says: `{e.text}`\n\n"
                f"Fix: **Server Settings → Roles → [Bot Role] → enable Administrator**"
            ))
            return
        except discord.HTTPException as e:
            await interaction.followup.send(embed=error_embed(
                f"Discord API error creating channels: `{e.status}` `{e.text}`"
            ))
            return

        # Create and save campaign state
        campaign = CampaignState(guild_id=str(guild.id))
        campaign.narration_channel_id = str(narration_ch.id)
        campaign.log_channel_id = str(log_ch.id)
        campaign.player_channel_ids = player_channel_ids
        campaign.category_id = str(category.id)
        campaign.player_ids = player_ids
        campaign.quests = [q.to_dict() for q in STARTING_QUESTS]
        campaign.important_npcs = {
            "Gundren Rockseeker": "Your employer. Stout dwarf merchant. Currently missing.",
            "Sildar Hallwinter": "Gundren's bodyguard. Warrior, Lords' Alliance. Captured by goblins.",
        }
        await db.save_campaign(campaign)

        # AI narration — non-fatal, falls back to static text if API unavailable
        location = LOCATIONS.get("sword_coast_road", {})
        try:
            narration = await narrate_scene(
                location_name=location.get("name", "Sword Coast Road"),
                location_description=location.get("description", ""),
                chapter=1,
                recent_events=["The party has been hired by Gundren Rockseeker to escort supplies to Phandalin."],
            )
        except Exception:
            narration = (
                "The road east winds through dark pine forest. Birdsong fades behind you as Neverwinter "
                "disappears over the horizon. Somewhere ahead, Phandalin waits — and with it, Gundren's secrets."
            )

        narration_message = (
            f"**The adventure begins...**\n\n"
            f"*Players: {', '.join(m.display_name for m in player_members)}*\n\n"
            f"{narration}\n\n"
            f"*Gundren hired you to escort a wagon of supplies to Phandalin — 10 gp each, "
            f"10 more on delivery to Barthen's Provisions. He and his bodyguard Sildar rode ahead.*"
        )
        await narration_ch.send(embed=narration_embed(narration_message, "Chapter 1: Goblin Arrows", "Sword Coast Road"))

        # Post starting quests to log channel
        for q in STARTING_QUESTS:
            await log_ch.send(embed=quest_embed(q))

        # Welcome message in each player's private channel — prompts character creation
        from utils.views import CharacterCreationView
        for member in player_members:
            ch_id = player_channel_ids.get(str(member.id))
            if ch_id:
                ch = guild.get_channel(int(ch_id))
                if ch:
                    await ch.send(embed=info_embed(
                        f"Welcome to Lost Mines of Phandelver, {member.display_name}!",
                        "Before your journey begins — **who are you?**\n\n"
                        "Press the button below to create your character. "
                        "Choose your name, race, and class, and your ability scores "
                        "will be rolled and assigned automatically.\n\n"
                        "**Races:** Human, Elf, Dwarf, Halfling, Half-Elf, "
                        "Half-Orc, Gnome, Dragonborn, Tiefling\n"
                        "**Classes:** Fighter, Wizard, Rogue, Cleric, Ranger, "
                        "Paladin, Barbarian, Bard\n\n"
                        "*Once your character is created, your adventure buttons will appear here.*"
                    ), view=CharacterCreationView())

        # Confirm in the invoking channel
        await interaction.followup.send(embed=success_embed(
            f"Campaign started with {len(player_members)} players!\n"
            f"📖 Narration: {narration_ch.mention}\n"
            f"📋 Game Log: {log_ch.mention}\n"
            f"Check your private channel for setup instructions."
        ))

    # ------------------------------------------------------------------
    # /game status
    # ------------------------------------------------------------------

    @app_commands.command(name="game_status", description="Show campaign overview")
    async def game_status(self, interaction: discord.Interaction):
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.response.send_message(
                embed=error_embed("No active campaign. Use `/game_start` to begin."), ephemeral=True
            )
            return

        player_count = len(campaign.player_ids)
        embed = campaign_status_embed(campaign, player_count)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ------------------------------------------------------------------
    # /game location
    # ------------------------------------------------------------------

    @app_commands.command(name="game_location", description="Narrate the current location")
    async def game_location(self, interaction: discord.Interaction):
        await interaction.response.defer()
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."), ephemeral=True)
            return

        location_key = campaign.current_location.lower().replace(" ", "_")
        loc_data = LOCATIONS.get(location_key, {
            "name": campaign.current_location,
            "description": "The party stands in an unfamiliar place.",
        })

        try:
            narration = await narrate_scene(
                location_name=loc_data.get("name", campaign.current_location),
                location_description=loc_data.get("description", ""),
                chapter=campaign.chapter,
            )
        except Exception:
            narration = loc_data.get("description", "The party surveys their surroundings.")

        if campaign.narration_channel_id:
            ch = interaction.guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=narration_embed(narration, loc_data.get("name", campaign.current_location)))

        await self._maybe_trigger_combat(interaction, campaign, loc_data)
        await interaction.followup.send(embed=success_embed("Scene posted to narration channel."), ephemeral=True)

    # ------------------------------------------------------------------
    # /game travel
    # ------------------------------------------------------------------

    @app_commands.command(name="game_travel", description="Move the party to a new location")
    @app_commands.describe(location="Location name (e.g. 'Phandalin', 'Cragmaw Hideout')")
    async def game_travel(self, interaction: discord.Interaction, location: str):
        await interaction.response.defer()
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."), ephemeral=True)
            return

        location_key = location.lower().replace(" ", "_")
        loc_data = LOCATIONS.get(location_key, {
            "name": location, "description": f"The party travels to {location}.",
        })

        campaign.current_location = loc_data.get("name", location)
        if campaign.current_location not in campaign.discovered_locations:
            campaign.discovered_locations.append(campaign.current_location)
        await db.save_campaign(campaign)

        try:
            narration = await narrate_scene(
                location_name=loc_data.get("name", location),
                location_description=loc_data.get("description", ""),
                chapter=campaign.chapter,
            )
        except Exception:
            narration = loc_data.get("description", f"The party arrives at {location}.")

        if campaign.narration_channel_id:
            ch = interaction.guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=narration_embed(narration, f"Arriving at {loc_data.get('name', location)}"))

        await self._maybe_trigger_combat(interaction, campaign, loc_data)
        await interaction.followup.send(
            embed=success_embed(f"Party traveled to **{campaign.current_location}**."), ephemeral=True
        )

    async def _maybe_trigger_combat(self, interaction: discord.Interaction, campaign, loc_data: dict):
        """Check if the AI thinks combat should start immediately at this location."""
        from ai.narrator import should_trigger_combat
        from data.campaign.lmop import ENCOUNTERS, get_encounter

        # Only trigger if location has a default encounter that hasn't been completed
        encounter_key = loc_data.get("default_encounter")
        if not encounter_key:
            return

        # Don't re-trigger if already defeated
        encounter_data = get_encounter(encounter_key)
        if not encounter_data:
            return
        flag = encounter_data.get("story_flag")
        if flag and campaign.story_flags.get(flag):
            return

        # Don't trigger if combat already active
        existing = await db.load_combat(str(interaction.guild_id))
        if existing and existing.is_active:
            return

        # Ask the AI
        try:
            start, reason = await should_trigger_combat(
                location_name=loc_data.get("name", ""),
                location_description=loc_data.get("description", ""),
                available_encounter=encounter_key,
                encounter_description=encounter_data.get("description", ""),
                story_flags=campaign.story_flags,
                chapter=campaign.chapter,
            )
        except Exception:
            return

        if not start:
            return

        # Trigger the encounter automatically
        from data.models import Character
        from engine.combat_engine import start_encounter
        from ai.narrator import narrate_encounter_start

        characters = []
        for pid in campaign.player_ids:
            char = await db.load_character(pid, str(interaction.guild_id))
            if char:
                characters.append(char)

        if not characters:
            return

        combat, order_str = start_encounter(encounter_key, characters, encounter_data)
        await db.save_combat(str(interaction.guild_id), combat)

        monster_names = list({
            __import__('data.models', fromlist=['Monster']).Monster.from_dict(m).name
            for m in combat.monsters.values()
        })

        try:
            enc_narration = await narrate_encounter_start(
                encounter_name=encounter_data.get("name", encounter_key),
                encounter_description=encounter_data.get("description", ""),
                monster_names=monster_names,
                location=loc_data.get("name", ""),
            )
        except Exception:
            enc_narration = encounter_data.get("description", "Combat begins!")

        if campaign.narration_channel_id:
            narr_ch = interaction.guild.get_channel(int(campaign.narration_channel_id))
            if narr_ch:
                from utils.embeds import combat_embed, narration_embed
                await narr_ch.send(embed=narration_embed(enc_narration, f"⚔️ {encounter_data.get('name', encounter_key)}"))
                await narr_ch.send(embed=combat_embed("Initiative Order", order_str, "Combat begins!"))

        await db.append_log(str(interaction.guild_id), "combat",
            f"Auto-triggered encounter: {encounter_data.get('name', encounter_key)} — {reason}")

        # Notify each player
        from utils.views import ExplorationView
        for pid in campaign.player_ids:
            ch_id = campaign.player_channel_ids.get(pid)
            if ch_id:
                ch = interaction.guild.get_channel(int(ch_id))
                if ch:
                    from utils.embeds import info_embed
                    from engine.combat_engine import get_turn_tracking
                    from engine.action_validator import get_available_actions_text
                    char = await db.load_character(pid, str(interaction.guild_id))
                    if char:
                        turn = get_turn_tracking(combat, pid)
                        await ch.send(embed=info_embed(
                            "⚔️ Combat! (Auto-triggered)",
                            f"*{reason}*\n\n"
                            + get_available_actions_text(char, turn)
                            + "\n\nUse the buttons below or `/combat_action`, `/combat_attack`, `/combat_cast`, or `/combat_end_turn`."
                        ))

        # Run any immediate monster turns
        from cogs.combat_cog import CombatCog
        combat_cog = self.bot.get_cog("CombatCog")
        if combat_cog:
            await combat_cog._run_monster_turns(interaction.guild, campaign, combat)

    # ------------------------------------------------------------------
    # /game npc
    # ------------------------------------------------------------------

    @app_commands.command(name="game_npc", description="Interact with an NPC")
    @app_commands.describe(
        npc_name="Name of the NPC",
        message="What you say or do",
    )
    async def game_npc(self, interaction: discord.Interaction, npc_name: str, message: str):
        await interaction.response.defer()
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."), ephemeral=True)
            return

        from data.campaign.lmop import NPCS, get_npc
        from ai.narrator import narrate_npc_dialogue

        npc_key = npc_name.lower().replace(" ", "_")
        npc = get_npc(npc_key)
        if not npc:
            # Try partial match
            for k, v in NPCS.items():
                if npc_name.lower() in v["name"].lower():
                    npc = v
                    break

        if not npc:
            npc = {"name": npc_name, "description": "A person of unknown background."}

        context = f"Chapter {campaign.chapter}, Location: {campaign.current_location}"
        response = await narrate_npc_dialogue(
            npc_name=npc["name"],
            npc_description=npc.get("description", ""),
            player_said=message,
            campaign_context=context,
        )

        if campaign.narration_channel_id:
            ch = interaction.guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=narration_embed(response, f"💬 {npc['name']}"))

        await interaction.followup.send(embed=success_embed("NPC response posted to narration channel."), ephemeral=True)

    # ------------------------------------------------------------------
    # /game end
    # ------------------------------------------------------------------

    @app_commands.command(name="game_end", description="End the campaign and remove all campaign channels")
    async def game_end(self, interaction: discord.Interaction):
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.response.send_message(embed=error_embed("No active campaign."), ephemeral=True)
            return

        await interaction.response.send_message(
            "⚠️ This will delete all campaign channels and data. Are you sure? (Reply 'confirm' within 30 seconds)",
            ephemeral=True,
        )

        def check(m):
            return m.author == interaction.user and m.content.lower() == "confirm"

        try:
            await self.bot.wait_for("message", check=check, timeout=30)
        except Exception:
            await interaction.followup.send(embed=info_embed("Cancelled", "Campaign end cancelled."), ephemeral=True)
            return

        await cleanup_campaign_channels(interaction.guild, campaign.category_id)
        await db.delete_campaign(str(interaction.guild_id))
        await interaction.followup.send("✅ Campaign ended and channels cleaned up.", ephemeral=True)

    # ------------------------------------------------------------------
    # /quest list
    # ------------------------------------------------------------------

    @app_commands.command(name="quest_list", description="Show all quests")
    async def quest_list(self, interaction: discord.Interaction):
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.response.send_message(embed=error_embed("No active campaign."), ephemeral=True)
            return

        if not campaign.quests:
            await interaction.response.send_message(embed=info_embed("Quests", "No active quests."), ephemeral=True)
            return

        embeds = [quest_embed(Quest.from_dict(q)) for q in campaign.quests]
        await interaction.response.send_message(embeds=embeds[:10], ephemeral=True)

    # ------------------------------------------------------------------
    # /log summary
    # ------------------------------------------------------------------

    @app_commands.command(name="log_summary", description="Show session summaries")
    async def log_summary(self, interaction: discord.Interaction):
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.response.send_message(embed=error_embed("No active campaign."), ephemeral=True)
            return

        if not campaign.session_summaries:
            await interaction.response.send_message(
                embed=info_embed("Session Summaries", "No summaries yet. Complete some encounters!"),
                ephemeral=True,
            )
            return

        text = "\n\n".join(f"**Session {i+1}:** {s}" for i, s in enumerate(campaign.session_summaries[-5:]))
        await interaction.response.send_message(
            embed=info_embed("📖 Campaign So Far", text), ephemeral=False
        )

    # ------------------------------------------------------------------
    # /log combat
    # ------------------------------------------------------------------

    @app_commands.command(name="log_combat", description="Show recent combat log entries")
    async def log_combat(self, interaction: discord.Interaction):
        logs = await db.get_logs(str(interaction.guild_id), log_type="combat", limit=15)
        if not logs:
            await interaction.response.send_message(
                embed=info_embed("Combat Log", "No combat log entries yet."), ephemeral=True
            )
            return

        lines = [f"`[{l['timestamp'][:16]}]` {l['content']}" for l in logs]
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3900] + "\n..."
        await interaction.response.send_message(embed=info_embed("⚔️ Combat Log", text), ephemeral=True)

    # ------------------------------------------------------------------
    # /log loot
    # ------------------------------------------------------------------

    @app_commands.command(name="log_loot", description="Show loot acquired this campaign")
    async def log_loot(self, interaction: discord.Interaction):
        logs = await db.get_logs(str(interaction.guild_id), log_type="loot", limit=20)
        if not logs:
            await interaction.response.send_message(
                embed=info_embed("Loot Log", "No loot recorded yet."), ephemeral=True
            )
            return

        lines = [f"• {l['content']}" for l in logs]
        await interaction.response.send_message(
            embed=info_embed("💰 Loot Acquired", "\n".join(lines)), ephemeral=False
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(GameCog(bot))
