"""
Non-combat actions cog.
Covers exploration, skill checks, NPC interaction, looting, and
free-form actions the AI interprets as the Dungeon Master.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands

import data.database as db
from data.models import Character
from data.campaign.lmop import LOCATIONS, get_npc, NPCS
from engine.dice import roll_d20, roll_dice
from engine.rules import SKILL_ABILITIES, CONDITIONS
from ai.narrator import narrate_scene, narrate_npc_dialogue
from utils.embeds import (
    narration_embed, info_embed, error_embed, success_embed,
)


SKILLS = [
    "acrobatics", "animal handling", "arcana", "athletics", "deception",
    "history", "insight", "intimidation", "investigation", "medicine",
    "nature", "perception", "performance", "persuasion", "religion",
    "sleight of hand", "stealth", "survival",
]


class ActionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _post_narration(self, guild, campaign, text: str, title: str = ""):
        if campaign and campaign.narration_channel_id:
            ch = guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=narration_embed(text, title))

    # ------------------------------------------------------------------
    # /action look — describe the current scene
    # ------------------------------------------------------------------

    @app_commands.command(name="action_look", description="Look around and describe the scene")
    async def action_look(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."))
            return

        location_key = campaign.current_location.lower().replace(" ", "_")
        loc = LOCATIONS.get(location_key, {
            "name": campaign.current_location,
            "description": "You survey your surroundings carefully.",
        })

        try:
            narration = await narrate_scene(
                location_name=loc.get("name", campaign.current_location),
                location_description=loc.get("description", ""),
                chapter=campaign.chapter,
            )
        except Exception:
            narration = loc.get("description", "You take in your surroundings.")

        await self._post_narration(interaction.guild, campaign, narration,
                                   f"📍 {campaign.current_location}")
        await interaction.followup.send(
            embed=success_embed("Scene description posted to narration channel.")
        )

    # ------------------------------------------------------------------
    # /action examine — inspect a specific object or area
    # ------------------------------------------------------------------

    @app_commands.command(name="action_examine", description="Closely examine something in the scene")
    @app_commands.describe(target="What you want to examine (e.g. 'the door', 'the chest', 'the goblin's belt')")
    async def action_examine(self, interaction: discord.Interaction, target: str):
        await interaction.response.defer(ephemeral=True)
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."))
            return

        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        char_name = char.name if char else interaction.user.display_name

        # Passive Investigation roll
        inv_mod = char.ability_scores.int_mod + char.proficiency_bonus if char else 0
        roll = roll_d20()
        total = roll + inv_mod

        from ai.narrator import get_client, NARRATOR_SYSTEM
        try:
            client = get_client()
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                system=NARRATOR_SYSTEM,
                messages=[{"role": "user", "content":
                    f"Location: {campaign.current_location}\n"
                    f"Character {char_name} examines: {target}\n"
                    f"Investigation roll: {total} (d20={roll} + {inv_mod})\n\n"
                    f"Describe what they find. If the roll is 15+ reveal something useful or hidden. "
                    f"If below 10, they notice nothing remarkable. 1-3 sentences."
                }],
            )
            narration = msg.content[0].text.strip()
        except Exception:
            if total >= 15:
                narration = f"**{char_name}** examines {target} closely and notices something interesting..."
            elif total >= 10:
                narration = f"**{char_name}** looks over {target} but finds nothing out of the ordinary."
            else:
                narration = f"**{char_name}** gives {target} a cursory glance and moves on."

        await self._post_narration(interaction.guild, campaign,
                                   narration, f"🔍 Examining: {target}")
        await interaction.followup.send(
            embed=info_embed("Examine", f"Investigation: **{total}** (d20 {roll} + {inv_mod})\nResult posted to narration channel.")
        )

    # ------------------------------------------------------------------
    # /action skill — make a skill check
    # ------------------------------------------------------------------

    @app_commands.command(name="action_skill", description="Make a skill check")
    @app_commands.describe(
        skill="The skill to use (e.g. perception, stealth, persuasion)",
        description="What you are trying to do",
        dc="Difficulty class (optional — DM sets if omitted)",
    )
    async def action_skill(self, interaction: discord.Interaction,
                           skill: str, description: str, dc: int = 0):
        await interaction.response.defer(ephemeral=False)

        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.followup.send(embed=error_embed("No character found. Create one with `/character_create`."))
            return

        skill_lower = skill.lower()
        ability = SKILL_ABILITIES.get(skill_lower)
        if not ability:
            close = [s for s in SKILLS if skill_lower in s]
            suggestion = f" Did you mean: `{'`, `'.join(close[:3])}`?" if close else ""
            await interaction.followup.send(embed=error_embed(f"Unknown skill: `{skill}`.{suggestion}"))
            return

        # Get modifier
        ab = char.ability_scores
        ability_mod = {
            "strength": ab.str_mod, "dexterity": ab.dex_mod,
            "constitution": ab.con_mod, "intelligence": ab.int_mod,
            "wisdom": ab.wis_mod, "charisma": ab.cha_mod,
        }.get(ability, 0)

        prof = char.proficiency_bonus if skill_lower.title() in char.skill_proficiencies else 0
        roll = roll_d20()
        total = roll + ability_mod + prof

        # Build result
        prof_text = f" + {prof} prof" if prof else ""
        roll_detail = f"d20 ({roll}) + {ability_mod} {ability[:3].upper()}{prof_text} = **{total}**"

        if dc:
            outcome = "✅ **Success!**" if total >= dc else "❌ **Failure**"
            result_line = f"{roll_detail} vs DC {dc} — {outcome}"
        else:
            result_line = roll_detail

        # AI narrates the attempt
        campaign = await db.load_campaign(str(interaction.guild_id))
        try:
            from ai.narrator import get_client, NARRATOR_SYSTEM
            client = get_client()
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=150,
                system=NARRATOR_SYSTEM,
                messages=[{"role": "user", "content":
                    f"{char.name} attempts: {description}\n"
                    f"Skill: {skill.title()} — roll total: {total}"
                    + (f" vs DC {dc}" if dc else "") + "\n"
                    f"{'Success.' if dc and total >= dc else 'Failure.' if dc else ''}\n\n"
                    f"Narrate the attempt in 1-2 sentences."
                }],
            )
            narration = msg.content[0].text.strip()
        except Exception:
            narration = f"**{char.name}** attempts {description}."

        if campaign:
            await self._post_narration(interaction.guild, campaign, narration)

        await interaction.followup.send(embed=info_embed(
            f"🎲 {skill.title()} Check",
            f"**{char.name}**: {description}\n\n{result_line}"
        ))

    # ------------------------------------------------------------------
    # /action search — search the area (Perception/Investigation)
    # ------------------------------------------------------------------

    @app_commands.command(name="action_search", description="Search the area for hidden things (traps, secrets, loot)")
    async def action_search(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        campaign = await db.load_campaign(str(interaction.guild_id))

        # Perception + Investigation
        perc_mod = char.ability_scores.wis_mod + (
            char.proficiency_bonus if "Perception" in char.skill_proficiencies else 0
        )
        inv_mod = char.ability_scores.int_mod + (
            char.proficiency_bonus if "Investigation" in char.skill_proficiencies else 0
        )
        perc_roll = roll_d20() + perc_mod
        inv_roll = roll_d20() + inv_mod
        best = max(perc_roll, inv_roll)

        location_name = campaign.current_location if campaign else "the area"

        try:
            from ai.narrator import get_client, NARRATOR_SYSTEM
            client = get_client()
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                system=NARRATOR_SYSTEM,
                messages=[{"role": "user", "content":
                    f"Location: {location_name}\n"
                    f"{char.name} searches the area.\n"
                    f"Perception: {perc_roll}, Investigation: {inv_roll} (best: {best})\n\n"
                    f"Describe what they find. 15+ reveals something hidden or useful. "
                    f"10-14 finds nothing remarkable. Under 10 finds nothing. 2 sentences max."
                }],
            )
            narration = msg.content[0].text.strip()
        except Exception:
            if best >= 15:
                narration = f"**{char.name}** searches carefully and spots something others might have missed."
            else:
                narration = f"**{char.name}** searches the area but finds nothing immediately obvious."

        if campaign:
            await self._post_narration(interaction.guild, campaign, narration, "🔎 Search")

        await interaction.followup.send(embed=info_embed(
            "🔎 Search",
            f"Perception: **{perc_roll}** | Investigation: **{inv_roll}**\n"
            f"Result posted to narration channel."
        ))

    # ------------------------------------------------------------------
    # /action talk — speak to an NPC
    # ------------------------------------------------------------------

    @app_commands.command(name="action_talk", description="Talk to an NPC")
    @app_commands.describe(
        npc="NPC name (e.g. Sildar, Gundren, Toblen)",
        message="What you say or ask",
    )
    async def action_talk(self, interaction: discord.Interaction, npc: str, message: str):
        await interaction.response.defer(ephemeral=True)
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."))
            return

        # Find NPC data
        npc_key = npc.lower().replace(" ", "_")
        npc_data = get_npc(npc_key)
        if not npc_data:
            for k, v in NPCS.items():
                if npc.lower() in v["name"].lower():
                    npc_data = v
                    break
        if not npc_data:
            npc_data = {"name": npc, "description": "A person of unknown background."}

        context = f"Chapter {campaign.chapter}, Location: {campaign.current_location}"
        try:
            response = await narrate_npc_dialogue(
                npc_name=npc_data["name"],
                npc_description=npc_data.get("description", ""),
                player_said=message,
                campaign_context=context,
            )
        except Exception:
            response = f'*{npc_data["name"]} listens carefully.* "I\'ll keep that in mind," they say.'

        await self._post_narration(interaction.guild, campaign,
                                   response, f"💬 {npc_data['name']}")
        await interaction.followup.send(
            embed=success_embed("NPC response posted to narration channel.")
        )

    # ------------------------------------------------------------------
    # /action sneak — attempt to move stealthily
    # ------------------------------------------------------------------

    @app_commands.command(name="action_sneak", description="Attempt to move without being noticed (Stealth check)")
    async def action_sneak(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        dex_mod = char.ability_scores.dex_mod
        prof = char.proficiency_bonus if "Stealth" in char.skill_proficiencies else 0
        roll = roll_d20()
        total = roll + dex_mod + prof

        # Check for armor stealth disadvantage
        heavy_armor = any(
            "disadvantage on Stealth" in str(i.properties)
            for i in char.inventory if i.equipped and i.item_type == "armor"
        )
        if heavy_armor:
            roll2 = roll_d20()
            total = min(roll, roll2) + dex_mod + prof
            note = f" (disadvantage — heavy armor: rolls {roll} & {roll2})"
        else:
            note = f" (d20 {roll} + {dex_mod} DEX" + (f" + {prof} prof)" if prof else ")")

        await interaction.followup.send(embed=info_embed(
            "🤫 Stealth Check",
            f"**{char.name}** attempts to move silently.\n"
            f"Stealth: **{total}**{note}\n\n"
            f"The DM will tell you if you succeed."
        ))

    # ------------------------------------------------------------------
    # /action loot — loot fallen enemies after combat
    # ------------------------------------------------------------------

    @app_commands.command(name="action_loot", description="Loot fallen enemies after combat")
    async def action_loot(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        campaign = await db.load_campaign(str(interaction.guild_id))
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."))
            return

        # Check there's no active combat
        combat = await db.load_combat(str(interaction.guild_id))
        if combat and combat.is_active:
            await interaction.followup.send(embed=error_embed(
                "Combat is still ongoing! Finish the fight first."
            ))
            return

        # Pull recent loot logs
        logs = await db.get_logs(str(interaction.guild_id), log_type="loot", limit=3)
        if logs:
            recent = logs[0]["content"]
            await interaction.followup.send(embed=info_embed(
                "💰 Loot",
                f"Most recent loot from this campaign:\n\n"
                + "\n".join(f"• {l['content']}" for l in logs)
                + "\n\nUse `/log_loot` for the full loot history."
            ))
        else:
            await interaction.followup.send(embed=info_embed(
                "💰 Loot",
                "No loot has been recorded yet. Defeat enemies in an encounter to earn rewards.\n\n"
                "Start a fight with `/combat_encounter`."
            ))

    # ------------------------------------------------------------------
    # /action do — free-form action, AI interprets as DM
    # ------------------------------------------------------------------

    @app_commands.command(name="action_do", description="Describe any action — the DM will narrate the outcome")
    @app_commands.describe(description="What your character does (e.g. 'I pick the lock', 'I intimidate the guard')")
    async def action_do(self, interaction: discord.Interaction, description: str):
        await interaction.response.defer(ephemeral=False)

        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        campaign = await db.load_campaign(str(interaction.guild_id))

        char_name = char.name if char else interaction.user.display_name
        location = campaign.current_location if campaign else "unknown location"

        # Determine if a skill roll is needed and roll it
        roll = roll_d20()
        ability_context = ""
        if char:
            # Guess relevant ability from keywords
            desc_lower = description.lower()
            if any(w in desc_lower for w in ["climb", "swim", "jump", "push", "force", "break", "lift"]):
                mod = char.ability_scores.str_mod; stat = "STR"
            elif any(w in desc_lower for w in ["sneak", "hide", "pick", "lockpick", "acrobat", "balance", "tumble", "sleight"]):
                mod = char.ability_scores.dex_mod; stat = "DEX"
            elif any(w in desc_lower for w in ["arcana", "history", "identify", "recall", "know", "investigate", "research"]):
                mod = char.ability_scores.int_mod; stat = "INT"
            elif any(w in desc_lower for w in ["perceive", "notice", "spot", "listen", "sense", "survive", "track", "heal", "medicine", "insight"]):
                mod = char.ability_scores.wis_mod; stat = "WIS"
            elif any(w in desc_lower for w in ["persuade", "deceive", "intimidate", "perform", "bluff", "charm", "negotiate"]):
                mod = char.ability_scores.cha_mod; stat = "CHA"
            else:
                mod = 0; stat = ""

            if stat:
                total = roll + mod
                ability_context = f"Roll: d20 ({roll}) + {mod} {stat} = **{total}**"
            else:
                ability_context = f"d20 roll: **{roll}**"

        try:
            from ai.narrator import get_client, NARRATOR_SYSTEM
            client = get_client()
            msg = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=250,
                system=NARRATOR_SYSTEM,
                messages=[{"role": "user", "content":
                    f"Location: {location}\n"
                    f"Character: {char_name}"
                    + (f" ({char.race} {char.char_class} level {char.level})" if char else "") + "\n"
                    f"Action: {description}\n"
                    f"{ability_context}\n\n"
                    f"As DM, narrate the outcome of this action. "
                    f"Use the roll to determine success/failure/degree. "
                    f"15+ is a clear success, 10-14 is partial, under 10 is a failure with consequences. "
                    f"2-3 vivid sentences."
                }],
            )
            narration = msg.content[0].text.strip()
        except Exception:
            narration = f"**{char_name}** {description}."

        if campaign:
            await self._post_narration(interaction.guild, campaign, narration)

        await interaction.followup.send(embed=info_embed(
            f"⚡ {char_name}: {description[:50]}{'...' if len(description) > 50 else ''}",
            f"{ability_context}\n\nNarration posted to the narration channel."
        ))

    # ------------------------------------------------------------------
    # /action conditions — list all D&D conditions and their effects
    # ------------------------------------------------------------------

    @app_commands.command(name="action_conditions", description="Look up a D&D 5e condition (poisoned, prone, etc.)")
    @app_commands.describe(condition="Condition name, or leave blank to list all")
    async def action_conditions(self, interaction: discord.Interaction, condition: str = ""):
        if condition:
            cond_lower = condition.lower()
            effect = CONDITIONS.get(cond_lower)
            if effect:
                await interaction.response.send_message(
                    embed=info_embed(f"⚠️ {condition.title()}", effect), ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=error_embed(f"Unknown condition: `{condition}`\nValid: {', '.join(CONDITIONS.keys())}"),
                    ephemeral=True,
                )
        else:
            lines = [f"**{k.title()}**: {v[:80]}..." for k, v in CONDITIONS.items()]
            await interaction.response.send_message(
                embed=info_embed("📋 D&D 5e Conditions", "\n".join(lines)), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(ActionsCog(bot))
