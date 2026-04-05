"""
Combat management cog for Lost Mines of Phandelver D&D bot.
Full D&D 5e combat: initiative, action economy, attacks, spells, death saves.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

import data.database as db
from data.models import Character, Monster, CombatState
from data.campaign.lmop import get_encounter, ENCOUNTERS
from engine.combat_engine import (
    start_encounter, get_combat_status, resolve_melee_attack, resolve_spell,
    make_death_save, resolve_monster_turn, get_character_from_combat,
    get_monster_from_combat, save_character_to_combat, save_monster_to_combat,
    is_combat_over,
)
from engine.action_validator import (
    validate_it_is_your_turn, validate_action_available,
    validate_target, consume_action, consume_movement,
    ValidationError, get_available_actions_text, get_turn_tracking,
)
from engine.dice import roll_d20, roll_dice
from ai.narrator import narrate_encounter_start, narrate_combat_action, narrate_victory, narrate_defeat
from ai.action_parser import parse_player_action
from utils.embeds import combat_embed, error_embed, success_embed, narration_embed, info_embed


class CombatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_narration_channel(self, guild: discord.Guild, campaign) -> Optional[discord.TextChannel]:
        if not campaign or not campaign.narration_channel_id:
            return None
        return guild.get_channel(int(campaign.narration_channel_id))

    async def _get_log_channel(self, guild: discord.Guild, campaign) -> Optional[discord.TextChannel]:
        if not campaign or not campaign.log_channel_id:
            return None
        return guild.get_channel(int(campaign.log_channel_id))

    async def _post_to_narration(self, guild: discord.Guild, campaign, embed: discord.Embed):
        ch = await self._get_narration_channel(guild, campaign)
        if ch:
            await ch.send(embed=embed)

    async def _run_monster_turns(self, combat: CombatState, guild: discord.Guild, campaign) -> CombatState:
        """
        After a player ends their turn, automatically run all consecutive monster turns
        until it's a player's turn again (or combat ends).
        """
        while combat.is_active:
            current_id = combat.current_combatant_id()
            if not current_id:
                break
            if current_id in combat.players:
                # Player's turn — stop
                break

            # Monster's turn
            monster = get_monster_from_combat(combat, current_id)
            if not monster or not monster.is_alive():
                combat.advance_turn()
                await db.save_combat(str(guild.id), combat)
                continue

            results = resolve_monster_turn(combat, current_id)
            for result in results:
                narr_text = await narrate_combat_action(
                    action_description=f"{monster.name} attacks",
                    mechanical_result=result.description,
                )
                await self._post_to_narration(guild, campaign, narration_embed(narr_text))
                await db.append_log(str(guild.id), "combat", result.description)

                # Check if a player died
                for event in result.events:
                    if "_defeated" in event:
                        for pid, pdata in combat.players.items():
                            char = Character.from_dict(pdata)
                            if not char.is_alive() and char.current_hp == 0:
                                await self._post_to_narration(
                                    guild, campaign,
                                    narration_embed(f"💀 **{char.name}** falls unconscious!")
                                )

            over, reason = is_combat_over(combat)
            if over:
                await self._handle_combat_end(combat, reason, guild, campaign)
                return combat

            combat.advance_turn()
            await db.save_combat(str(guild.id), combat)

        return combat

    async def _handle_combat_end(self, combat: CombatState, reason: str, guild: discord.Guild, campaign):
        """Handle end of combat: narrate, award XP, loot, update campaign."""
        combat.is_active = False
        guild_id = str(guild.id)

        # Get encounter data for loot/xp
        encounter_key = combat.encounter_name.lower().replace(" — ", "_").replace(" - ", "_").replace(" ", "_")
        encounter_data = ENCOUNTERS.get(encounter_key, {})
        loot = encounter_data.get("loot", [])
        xp_reward = encounter_data.get("xp", 0)

        if reason == "victory":
            fallen_enemies = [
                Monster.from_dict(m).name for m in combat.monsters.values()
            ]
            narr = await narrate_victory(
                encounter_name=combat.encounter_name,
                fallen_enemies=fallen_enemies,
                location=combat.location,
                loot=loot if loot else None,
            )
            await self._post_to_narration(guild, campaign, narration_embed(narr, "⚔️ Victory!"))

            # Award XP
            if xp_reward and campaign and campaign.player_ids:
                xp_each = xp_reward // len(campaign.player_ids)
                for pid in campaign.player_ids:
                    char = await db.load_character(pid, guild_id)
                    if char:
                        char.experience_points += xp_each
                        await db.save_character(char, guild_id)
                xp_msg = f"Each adventurer gains **{xp_each} XP**."
                await self._post_to_narration(guild, campaign, success_embed(xp_msg))

            # Log loot
            if loot:
                loot_lines = [f"{l.get('quantity', 1)}x {l['name']}" for l in loot]
                loot_text = "**Loot found:**\n" + "\n".join(f"• {item}" for item in loot_lines)
                log_ch = await self._get_log_channel(guild, campaign)
                if log_ch:
                    await log_ch.send(embed=success_embed(loot_text))
                for item in loot_lines:
                    await db.append_log(guild_id, "loot", f"{combat.encounter_name}: {item}")

            # Update story flag
            story_flag = encounter_data.get("story_flag")
            if story_flag and campaign:
                campaign.story_flags[story_flag] = True
                await db.save_campaign(campaign)

        else:  # defeat
            narr = await narrate_defeat()
            await self._post_to_narration(guild, campaign, narration_embed(narr, "💀 Defeat"))

        await db.delete_combat(guild_id)
        await db.append_log(guild_id, "combat", f"Combat ended: {combat.encounter_name} — {reason}")

    # ------------------------------------------------------------------
    # /combat_encounter
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_encounter", description="Start a named combat encounter")
    @app_commands.describe(encounter_name="Encounter key (e.g. goblin_ambush, cragmaw_hideout_klarg)")
    async def combat_encounter(self, interaction: discord.Interaction, encounter_name: str):
        await interaction.response.defer(ephemeral=False)
        guild_id = str(interaction.guild_id)

        campaign = await db.load_campaign(guild_id)
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."), ephemeral=True)
            return

        existing_combat = await db.load_combat(guild_id)
        if existing_combat and existing_combat.is_active:
            await interaction.followup.send(embed=error_embed("A combat is already active! Use `/combat_status`."), ephemeral=True)
            return

        # Find encounter
        encounter_key = encounter_name.lower().replace(" ", "_")
        encounter_data = get_encounter(encounter_key)
        if not encounter_data:
            # Try partial match
            for k, v in ENCOUNTERS.items():
                if encounter_key in k or encounter_key in v.get("name", "").lower():
                    encounter_data = v
                    encounter_key = k
                    break

        if not encounter_data:
            available = ", ".join(ENCOUNTERS.keys())
            await interaction.followup.send(embed=error_embed(
                f"Unknown encounter: `{encounter_name}`\nAvailable: {available}"
            ), ephemeral=True)
            return

        # Load all player characters
        characters = []
        for pid in campaign.player_ids:
            char = await db.load_character(pid, guild_id)
            if char and char.is_alive():
                characters.append(char)

        if not characters:
            await interaction.followup.send(embed=error_embed("No living player characters found. Create characters first."), ephemeral=True)
            return

        # Start encounter
        combat, initiative_order_str = start_encounter(encounter_key, characters, encounter_data)
        await db.save_combat(guild_id, combat)

        # Update campaign combat reference
        campaign.active_combat = {"encounter_id": combat.encounter_id, "encounter_key": encounter_key}
        await db.save_campaign(campaign)

        # Narrate encounter start
        monster_names = [
            Monster.from_dict(m).name for m in combat.monsters.values()
        ]
        narr = await narrate_encounter_start(
            encounter_name=encounter_data.get("name", encounter_name),
            encounter_description=encounter_data.get("description", ""),
            monster_names=monster_names,
            location=encounter_data.get("location", campaign.current_location),
        )

        narration_ch = await self._get_narration_channel(interaction.guild, campaign)
        if narration_ch:
            await narration_ch.send(embed=narration_embed(narr, f"⚔️ {encounter_data.get('name', encounter_name)}"))
            await narration_ch.send(embed=combat_embed(
                "Initiative Order", initiative_order_str,
                footer=f"Round 1 begins! It is {Character.from_dict(list(combat.players.values())[0]).name if combat.players else 'the enemy'}'s turn."
            ))

        # Notify the first player in their private channel
        first_id = combat.current_combatant_id()
        if first_id and first_id in combat.players:
            first_char = Character.from_dict(combat.players[first_id])
            ch_id = campaign.player_channel_ids.get(first_id)
            if ch_id:
                player_ch = interaction.guild.get_channel(int(ch_id))
                if player_ch:
                    await player_ch.send(embed=info_embed(
                        "⚔️ Your Turn!",
                        f"**{first_char.name}**, you go first!\n\n"
                        f"Use `/combat_action`, `/combat_attack`, `/combat_cast`, `/combat_move`, or other combat commands.\n"
                        f"Use `/character_actions` to see what's available this turn.\n"
                        f"End with `/combat_end_turn` when done."
                    ))

        await interaction.followup.send(embed=success_embed(
            f"Encounter started: **{encounter_data.get('name', encounter_name)}**\n"
            f"Check the narration channel for details."
        ))

    # ------------------------------------------------------------------
    # /combat_status
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_status", description="Show the current combat state")
    async def combat_status(self, interaction: discord.Interaction):
        combat = await db.load_combat(str(interaction.guild_id))
        if not combat or not combat.is_active:
            await interaction.response.send_message(embed=error_embed("No active combat."), ephemeral=True)
            return

        status_text = get_combat_status(combat)
        current_id = combat.current_combatant_id()
        if current_id and current_id in combat.players:
            current_name = Character.from_dict(combat.players[current_id]).name
        elif current_id and current_id in combat.monsters:
            current_name = Monster.from_dict(combat.monsters[current_id]).name
        else:
            current_name = "Unknown"

        from utils.embeds import combat_status_embed
        embed = combat_status_embed(status_text, combat.round_number, current_name)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ------------------------------------------------------------------
    # /combat_action (natural language AI-parsed)
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_action", description="Describe your action in plain English (AI-parsed)")
    @app_commands.describe(description="What you want to do (e.g. 'I cast fire bolt at the goblin' or 'I charge the bugbear with my sword')")
    async def combat_action(self, interaction: discord.Interaction, description: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        # Parse with AI
        available_spells = char.cantrips + char.prepared_spells + char.known_spells
        available_items = [item.name for item in char.inventory]
        is_rogue = char.char_class.lower() == "rogue"

        action_data = await parse_player_action(
            player_description=description,
            available_spells=available_spells,
            available_items=available_items,
            is_rogue=is_rogue,
        )

        action_type = action_data.get("action_type", "other")
        target_name = action_data.get("target")
        spell_name = action_data.get("spell_name")
        slot_level = action_data.get("spell_slot_level", 1)
        feet = action_data.get("movement_feet", 30)
        is_bonus = action_data.get("is_bonus_action", False)
        confidence = action_data.get("confidence", "low")
        action_key = "bonus_action" if is_bonus else "action"

        campaign = await db.load_campaign(guild_id)

        try:
            if action_type == "attack":
                turn = get_turn_tracking(combat, discord_id)
                validate_action_available(turn, "action")
                target_id, target_type = validate_target(combat, target_name or "")
                if target_type == "monster":
                    target = get_monster_from_combat(combat, target_id)
                else:
                    target = get_character_from_combat(combat, target_id)

                weapon = char.equipped_weapon()
                if weapon:
                    atk_bonus = (char.ability_scores.str_mod if "finesse" not in weapon.properties
                                 else max(char.ability_scores.str_mod, char.ability_scores.dex_mod))
                    atk_bonus += char.proficiency_bonus
                    result = resolve_melee_attack(char.name, atk_bonus, weapon.damage, weapon.damage_type, target)
                else:
                    result = resolve_melee_attack(char.name, char.proficiency_bonus + char.ability_scores.str_mod,
                                                  "1d4", "bludgeoning", target)

                consume_action(combat, discord_id, "action")
                if target_type == "monster":
                    save_monster_to_combat(combat, target)
                else:
                    save_character_to_combat(combat, target)
                await db.save_combat(guild_id, combat)

                narr = await narrate_combat_action(description, result.description)
                await self._post_to_narration(interaction.guild, campaign, narration_embed(narr))
                await db.append_log(guild_id, "combat", result.description)

                over, reason = is_combat_over(combat)
                if over:
                    await self._handle_combat_end(combat, reason, interaction.guild, campaign)

                await interaction.followup.send(embed=success_embed(f"Action taken. Check narration channel."))

            elif action_type == "spell" and spell_name:
                from engine.action_validator import validate_spell_known
                if not validate_spell_known(char, spell_name):
                    await interaction.followup.send(embed=error_embed(f"You don't know the spell: {spell_name}"))
                    return

                from data.campaign.spells import get_spell
                spell_data = get_spell(spell_name)
                action_kind = spell_data.get("action_type", "action") if spell_data else "action"
                turn = get_turn_tracking(combat, discord_id)
                validate_action_available(turn, action_kind)

                target = None
                if target_name:
                    try:
                        target_id, target_type = validate_target(combat, target_name)
                        if target_type == "monster":
                            target = get_monster_from_combat(combat, target_id)
                        else:
                            target = get_character_from_combat(combat, target_id)
                    except ValidationError:
                        pass

                result = resolve_spell(char, spell_name, slot_level or 1, target, combat)
                if result.error:
                    await interaction.followup.send(embed=error_embed(result.error))
                    return

                consume_action(combat, discord_id, action_kind)
                if target and hasattr(target, "monster_id"):
                    save_monster_to_combat(combat, target)
                elif target:
                    save_character_to_combat(combat, target)
                save_character_to_combat(combat, char)
                await db.save_combat(guild_id, combat)

                narr = await narrate_combat_action(description, result.description)
                await self._post_to_narration(interaction.guild, campaign, narration_embed(narr))

                over, reason = is_combat_over(combat)
                if over:
                    await self._handle_combat_end(combat, reason, interaction.guild, campaign)

                await interaction.followup.send(embed=success_embed("Spell cast. Check narration channel."))

            elif action_type == "move":
                turn = get_turn_tracking(combat, discord_id)
                move_feet = feet or 30
                validate_movement = __import__("engine.action_validator", fromlist=["validate_movement"]).validate_movement
                validate_movement(char, turn, move_feet)
                consume_movement(combat, discord_id, move_feet)
                await db.save_combat(guild_id, combat)
                await interaction.followup.send(embed=success_embed(f"**{char.name}** moves {move_feet} feet."))

            elif action_type in ("dash", "dodge", "hide", "disengage"):
                turn = get_turn_tracking(combat, discord_id)
                is_cunning = is_rogue and action_type in ("dash", "hide", "disengage")
                actual_action = "bonus_action" if is_cunning else "action"
                validate_action_available(turn, actual_action)
                consume_action(combat, discord_id, actual_action)

                effect_map = {
                    "dash": f"**{char.name}** dashes, doubling their movement speed this turn.",
                    "dodge": f"**{char.name}** takes the Dodge action. Attacks against them have disadvantage.",
                    "disengage": f"**{char.name}** disengages, avoiding opportunity attacks.",
                    "hide": f"**{char.name}** attempts to hide... (Stealth: {roll_d20() + char.ability_scores.dex_mod + char.proficiency_bonus})",
                }
                msg = effect_map.get(action_type, description)
                await db.save_combat(guild_id, combat)
                await self._post_to_narration(interaction.guild, campaign, success_embed(msg))
                await interaction.followup.send(embed=success_embed(f"Action taken."))

            else:
                # Low confidence / unknown — just narrate it
                narr = await narrate_combat_action(description, f"{char.name} acts: {description}")
                await self._post_to_narration(interaction.guild, campaign, narration_embed(narr))
                await interaction.followup.send(embed=info_embed(
                    "⚠️ Action unclear",
                    f"Confidence: {confidence}. Use specific commands like `/combat_attack`, `/combat_cast` for clearer results.",
                ))

        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))

    # ------------------------------------------------------------------
    # /combat_attack
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_attack", description="Make a weapon attack against a target")
    @app_commands.describe(target="Name of the enemy to attack")
    async def combat_attack(self, interaction: discord.Interaction, target: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        campaign = await db.load_campaign(guild_id)

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, "action")
            target_id, target_type = validate_target(combat, target)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        if target_type == "monster":
            target_obj = get_monster_from_combat(combat, target_id)
        else:
            target_obj = get_character_from_combat(combat, target_id)

        weapon = char.equipped_weapon()
        if weapon:
            # Check finesse
            use_dex = "finesse" in weapon.properties and char.ability_scores.dex_mod > char.ability_scores.str_mod
            stat_mod = char.ability_scores.dex_mod if use_dex else char.ability_scores.str_mod
            atk_bonus = stat_mod + char.proficiency_bonus
            result = resolve_melee_attack(char.name, atk_bonus, weapon.damage, weapon.damage_type, target_obj)
        else:
            # Unarmed strike
            atk_bonus = char.ability_scores.str_mod + char.proficiency_bonus
            result = resolve_melee_attack(char.name, atk_bonus, "1", "bludgeoning", target_obj)

        consume_action(combat, discord_id, "action")
        if target_type == "monster":
            save_monster_to_combat(combat, target_obj)
        else:
            save_character_to_combat(combat, target_obj)
        await db.save_combat(guild_id, combat)

        narr = await narrate_combat_action(
            action_description=f"{char.name} attacks {target_obj.name} with {weapon.name if weapon else 'bare hands'}",
            mechanical_result=result.description,
        )
        await self._post_to_narration(interaction.guild, campaign, narration_embed(narr))
        await db.append_log(guild_id, "combat", result.description)

        over, reason = is_combat_over(combat)
        if over:
            await self._handle_combat_end(combat, reason, interaction.guild, campaign)

        await interaction.followup.send(embed=success_embed("Attack resolved. Check the narration channel."))

    # ------------------------------------------------------------------
    # /combat_cast
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_cast", description="Cast a spell")
    @app_commands.describe(
        spell_name="Name of the spell to cast",
        target="Target name (optional)",
        slot_level="Spell slot level to use (default: spell's base level)",
    )
    async def combat_cast(
        self, interaction: discord.Interaction,
        spell_name: str,
        target: Optional[str] = None,
        slot_level: Optional[int] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        campaign = await db.load_campaign(guild_id)

        from engine.action_validator import validate_spell_known
        from data.campaign.spells import get_spell

        try:
            validate_it_is_your_turn(combat, discord_id)

            if not validate_spell_known(char, spell_name):
                await interaction.followup.send(embed=error_embed(f"You don't know **{spell_name}**."))
                return

            spell_data = get_spell(spell_name.lower())
            if not spell_data:
                await interaction.followup.send(embed=error_embed(f"Unknown spell: {spell_name}"))
                return

            actual_slot = slot_level if slot_level is not None else spell_data["level"]
            action_kind = spell_data.get("action_type", "action")
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, action_kind)

        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        # Resolve target
        target_obj = None
        if target:
            try:
                target_id, target_type = validate_target(combat, target)
                if target_type == "monster":
                    target_obj = get_monster_from_combat(combat, target_id)
                else:
                    target_obj = get_character_from_combat(combat, target_id)
            except ValidationError as e:
                await interaction.followup.send(embed=error_embed(str(e)))
                return

        result = resolve_spell(char, spell_name, actual_slot, target_obj, combat)
        if result.error:
            await interaction.followup.send(embed=error_embed(result.error))
            return

        consume_action(combat, discord_id, action_kind)
        if target_obj and hasattr(target_obj, "monster_id"):
            save_monster_to_combat(combat, target_obj)
        elif target_obj:
            save_character_to_combat(combat, target_obj)
        save_character_to_combat(combat, char)
        await db.save_combat(guild_id, combat)

        narr = await narrate_combat_action(
            action_description=f"{char.name} casts {spell_name}" + (f" at {target}" if target else ""),
            mechanical_result=result.description,
        )
        await self._post_to_narration(interaction.guild, campaign, narration_embed(narr))

        over, reason = is_combat_over(combat)
        if over:
            await self._handle_combat_end(combat, reason, interaction.guild, campaign)

        await interaction.followup.send(embed=success_embed(f"**{spell_name}** cast. Check narration channel."))

    # ------------------------------------------------------------------
    # /combat_move
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_move", description="Move up to N feet")
    @app_commands.describe(feet="Number of feet to move (up to your speed)")
    async def combat_move(self, interaction: discord.Interaction, feet: int):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            from engine.action_validator import validate_movement
            validate_movement(char, turn, feet)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        consume_movement(combat, discord_id, feet)
        await db.save_combat(guild_id, combat)

        remaining = char.speed - get_turn_tracking(combat, discord_id).movement_used
        await interaction.followup.send(embed=success_embed(
            f"**{char.name}** moves {feet} feet. ({remaining} feet remaining this turn)"
        ))

    # ------------------------------------------------------------------
    # /combat_dash
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_dash", description="Dash (use action to move extra distance)")
    async def combat_dash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        char = await db.load_character(discord_id, guild_id)
        campaign = await db.load_campaign(guild_id)

        if not combat or not combat.is_active or not char:
            await interaction.followup.send(embed=error_embed("No active combat or character."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            is_rogue = char.char_class.lower() == "rogue"
            action_key = "bonus_action" if is_rogue else "action"
            validate_action_available(turn, action_key)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        consume_action(combat, discord_id, action_key)
        await db.save_combat(guild_id, combat)
        msg = f"**{char.name}** dashes! They gain an extra {char.speed} feet of movement this turn."
        await self._post_to_narration(interaction.guild, campaign, success_embed(msg))
        await interaction.followup.send(embed=success_embed(msg))

    # ------------------------------------------------------------------
    # /combat_dodge
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_dodge", description="Dodge (attacks against you have disadvantage until your next turn)")
    async def combat_dodge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        char = await db.load_character(discord_id, guild_id)

        if not combat or not combat.is_active or not char:
            await interaction.followup.send(embed=error_embed("No active combat or character."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, "action")
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        consume_action(combat, discord_id, "action")
        if "dodging" not in char.conditions:
            char.conditions.append("dodging")
        await db.save_character(char, guild_id)
        save_character_to_combat(combat, char)
        await db.save_combat(guild_id, combat)
        await interaction.followup.send(embed=success_embed(
            f"**{char.name}** takes the Dodge action. Until your next turn, attacks against you have disadvantage."
        ))

    # ------------------------------------------------------------------
    # /combat_hide
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_hide", description="Attempt to hide (Stealth check)")
    async def combat_hide(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        char = await db.load_character(discord_id, guild_id)

        if not combat or not combat.is_active or not char:
            await interaction.followup.send(embed=error_embed("No active combat or character."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            is_rogue = char.char_class.lower() == "rogue"
            turn = get_turn_tracking(combat, discord_id)
            action_key = "bonus_action" if is_rogue else "action"
            validate_action_available(turn, action_key)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        stealth_roll = roll_d20() + char.ability_scores.dex_mod + char.proficiency_bonus
        consume_action(combat, discord_id, action_key)
        await db.save_combat(guild_id, combat)
        await interaction.followup.send(embed=info_embed(
            "🫥 Hide Attempt",
            f"**{char.name}** attempts to hide.\n"
            f"Stealth check: **{stealth_roll}** (d20 + DEX + Proficiency)\n"
            f"Enemies must beat this DC to spot you."
        ))

    # ------------------------------------------------------------------
    # /combat_disengage
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_disengage", description="Disengage (movement won't provoke opportunity attacks)")
    async def combat_disengage(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        char = await db.load_character(discord_id, guild_id)

        if not combat or not combat.is_active or not char:
            await interaction.followup.send(embed=error_embed("No active combat or character."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            is_rogue = char.char_class.lower() == "rogue"
            turn = get_turn_tracking(combat, discord_id)
            action_key = "bonus_action" if is_rogue else "action"
            validate_action_available(turn, action_key)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        consume_action(combat, discord_id, action_key)
        await db.save_combat(guild_id, combat)
        await interaction.followup.send(embed=success_embed(
            f"**{char.name}** disengages. Your movement this turn won't provoke opportunity attacks."
        ))

    # ------------------------------------------------------------------
    # /combat_end_turn
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_end_turn", description="End your turn and advance to the next combatant")
    async def combat_end_turn(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."), ephemeral=True)
            return

        campaign = await db.load_campaign(guild_id)

        try:
            validate_it_is_your_turn(combat, discord_id)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)), ephemeral=True)
            return

        # Advance turn
        combat.advance_turn()
        await db.save_combat(guild_id, combat)

        # Run any consecutive monster turns
        combat = await self._run_monster_turns(combat, interaction.guild, campaign)

        if not combat.is_active:
            await interaction.followup.send(embed=success_embed("Combat has ended. Check the narration channel."))
            return

        # Announce next player's turn
        next_id = combat.current_combatant_id()
        if next_id and next_id in combat.players:
            next_char = Character.from_dict(combat.players[next_id])
            next_ch_id = campaign.player_channel_ids.get(next_id) if campaign else None
            if next_ch_id:
                next_ch = interaction.guild.get_channel(int(next_ch_id))
                if next_ch:
                    turn = get_turn_tracking(combat, next_id)
                    actions_text = get_available_actions_text(next_char, turn)
                    await next_ch.send(embed=info_embed(
                        f"⚔️ Your Turn, {next_char.name}! (Round {combat.round_number})",
                        f"{actions_text}\n\nUse `/combat_action`, `/combat_attack`, `/combat_cast`, etc.\n"
                        f"End with `/combat_end_turn`."
                    ))

            # Post round transition to narration
            await self._post_to_narration(
                interaction.guild, campaign,
                info_embed(f"Round {combat.round_number}", f"It is now **{next_char.name}**'s turn.")
            )

        await interaction.followup.send(embed=success_embed("Turn ended. Monster turns resolved if any."))

    # ------------------------------------------------------------------
    # /combat_death_save
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_death_save", description="Make a death saving throw (when you have 0 HP)")
    async def combat_death_save(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        if char.current_hp > 0:
            await interaction.followup.send(embed=error_embed("You are not at 0 HP. Death saves are only for unconscious characters."))
            return

        combat = await db.load_combat(guild_id)
        campaign = await db.load_campaign(guild_id)

        result = make_death_save(char)
        await db.save_character(char, guild_id)

        if combat and combat.is_active:
            save_character_to_combat(combat, char)
            await db.save_combat(guild_id, combat)

        await self._post_to_narration(interaction.guild, campaign, info_embed("💀 Death Save", result.description))

        if "dead" in result.events:
            await interaction.followup.send(embed=error_embed(f"**{char.name}** has died. Three death save failures."))
        elif "stabilized" in result.events:
            await interaction.followup.send(embed=success_embed(f"**{char.name}** stabilizes!"))
        else:
            ds = char.death_saves
            await interaction.followup.send(embed=info_embed(
                "Death Save",
                f"Successes: {ds['successes']}/3 | Failures: {ds['failures']}/3"
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
