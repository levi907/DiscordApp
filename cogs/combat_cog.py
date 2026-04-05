"""
Combat cog — handles all in-combat slash commands.
Players declare actions here (from their private channels).
Narration is posted to the shared narration channel.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands

import data.database as db
from data.models import Character, Monster, CombatState
from data.campaign.lmop import get_encounter, ENCOUNTERS
from engine.combat_engine import (
    start_encounter, get_combat_status, is_combat_over,
    resolve_melee_attack, resolve_ranged_attack, resolve_spell,
    resolve_monster_turn, make_death_save,
    get_character_from_combat, get_monster_from_combat,
    save_character_to_combat, save_monster_to_combat,
    get_turn_tracking,
)
from engine.action_validator import (
    ValidationError, validate_it_is_your_turn, validate_action_available,
    validate_movement, validate_spell_slot, validate_spell_known,
    validate_target, consume_action, consume_movement,
    get_available_actions_text,
)
from engine.dice import roll_dice
from ai.narrator import (
    narrate_encounter_start, narrate_combat_action,
    narrate_victory, narrate_defeat,
)
from ai.action_parser import parse_player_action
from utils.embeds import (
    combat_embed, combat_status_embed, error_embed,
    success_embed, info_embed, narration_embed,
)


class CombatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_campaign_and_combat(self, guild_id: str):
        campaign = await db.load_campaign(guild_id)
        combat = await db.load_combat(guild_id) if campaign else None
        return campaign, combat

    async def _post_narration(self, guild: discord.Guild, campaign, text: str, title: str = ""):
        if campaign and campaign.narration_channel_id:
            ch = guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=narration_embed(text, title))

    async def _post_combat_status(self, guild: discord.Guild, campaign, combat: CombatState):
        """Post updated combat status to narration channel."""
        if not campaign or not campaign.narration_channel_id:
            return
        ch = guild.get_channel(int(campaign.narration_channel_id))
        if not ch:
            return
        status = get_combat_status(combat)
        current_id = combat.current_combatant_id()
        current_name = "Unknown"
        if current_id in combat.players:
            c = Character.from_dict(combat.players[current_id])
            current_name = c.name
        elif current_id in combat.monsters:
            m = Monster.from_dict(combat.monsters[current_id])
            current_name = m.name
        await ch.send(embed=combat_status_embed(status, combat.round_number, current_name))

    async def _run_monster_turns(self, guild: discord.Guild, campaign, combat: CombatState):
        """Automatically process all consecutive monster turns."""
        while True:
            current_id = combat.current_combatant_id()
            if not current_id or current_id not in combat.monsters:
                break

            monster = get_monster_from_combat(combat, current_id)
            if not monster or not monster.is_alive():
                combat.advance_turn()
                continue

            results = resolve_monster_turn(combat, current_id)
            for result in results:
                combat.add_log(result.description)
                narration = await narrate_combat_action(
                    action_description=f"{monster.name} attacks",
                    mechanical_result=result.description,
                )
                await self._post_narration(guild, campaign, narration)

                # Save updated characters back
                for pid in list(combat.players.keys()):
                    char = get_character_from_combat(combat, pid)
                    if char:
                        save_character_to_combat(combat, char)
                        await db.save_character(char, str(guild.id))

            combat.advance_turn()

            # Check if combat ended
            over, reason = is_combat_over(combat)
            if over:
                await self._end_combat(guild, campaign, combat, reason)
                return

        await db.save_combat(str(guild.id), combat)
        await self._post_combat_status(guild, campaign, combat)

    async def _end_combat(self, guild: discord.Guild, campaign, combat: CombatState, reason: str):
        """Handle combat end — victory or defeat."""
        guild_id = str(guild.id)
        combat.is_active = False
        await db.save_combat(guild_id, combat)

        encounter_data = ENCOUNTERS.get(combat.encounter_name.lower().replace(" — ", "_").replace(" ", "_"), {})
        fallen = [
            Monster.from_dict(m).name
            for m in combat.monsters.values()
            if not Monster.from_dict(m).is_alive()
        ]

        if reason == "victory":
            loot = encounter_data.get("loot", [])
            narration = await narrate_victory(
                encounter_name=combat.encounter_name,
                fallen_enemies=fallen,
                location=combat.location,
                loot=loot,
            )
            await self._post_narration(guild, campaign, narration, "⚔️ Victory!")

            # Award XP
            xp_gained = encounter_data.get("xp", 0)
            if xp_gained and campaign:
                xp_per_player = xp_gained // max(len(combat.players), 1)
                for pid in combat.players:
                    char = await db.load_character(pid, guild_id)
                    if char:
                        char.experience_points += xp_per_player
                        await db.save_character(char, guild_id)

                await db.append_log(guild_id, "combat",
                    f"Victory: {combat.encounter_name} — {xp_gained} XP ({xp_per_player} each)")

            # Log loot
            if loot:
                loot_str = ", ".join(f"{l.get('quantity',1)}x {l['name']}" for l in loot)
                await db.append_log(guild_id, "loot", f"{combat.encounter_name}: {loot_str}")

            # Story flag
            flag = encounter_data.get("story_flag")
            if flag and campaign:
                campaign.story_flags[flag] = True
                await db.save_campaign(campaign)

        else:
            narration = await narrate_defeat()
            await self._post_narration(guild, campaign, narration, "💀 Defeat")
            await db.append_log(guild_id, "combat", f"DEFEAT: {combat.encounter_name}")

        await db.delete_combat(guild_id)

    # ------------------------------------------------------------------
    # /combat_encounter — start an encounter
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_encounter", description="Start a combat encounter")
    @app_commands.describe(encounter_name="Encounter key (e.g. goblin_ambush, cragmaw_hideout_klarg)")
    async def combat_encounter(self, interaction: discord.Interaction, encounter_name: str):
        await interaction.response.defer()
        guild_id = str(interaction.guild_id)

        campaign = await db.load_campaign(guild_id)
        if not campaign:
            await interaction.followup.send(embed=error_embed("No active campaign."), ephemeral=True)
            return

        existing_combat = await db.load_combat(guild_id)
        if existing_combat and existing_combat.is_active:
            await interaction.followup.send(
                embed=error_embed("Combat is already active! Use `/combat_end_turn` to continue."),
                ephemeral=True,
            )
            return

        encounter_key = encounter_name.lower().replace(" ", "_")
        encounter_data = get_encounter(encounter_key)
        if not encounter_data:
            valid = ", ".join(ENCOUNTERS.keys())
            await interaction.followup.send(
                embed=error_embed(f"Unknown encounter: `{encounter_name}`\nValid: `{valid}`"),
                ephemeral=True,
            )
            return

        # Load all player characters
        characters = []
        for pid in campaign.player_ids:
            char = await db.load_character(pid, guild_id)
            if char:
                characters.append(char)

        if not characters:
            await interaction.followup.send(
                embed=error_embed("No characters found. Players must use `/character_create` first."),
                ephemeral=True,
            )
            return

        combat, order_str = start_encounter(encounter_key, characters, encounter_data)
        await db.save_combat(guild_id, combat)

        # AI narrate the encounter start
        monster_names = list({
            Monster.from_dict(m).name for m in combat.monsters.values()
        })
        narration = await narrate_encounter_start(
            encounter_name=encounter_data.get("name", encounter_name),
            encounter_description=encounter_data.get("description", ""),
            monster_names=monster_names,
            location=encounter_data.get("location", campaign.current_location),
        )

        await self._post_narration(
            interaction.guild, campaign, narration,
            f"⚔️ {encounter_data.get('name', encounter_name)}"
        )

        # Post initiative order to narration channel
        if campaign.narration_channel_id:
            ch = interaction.guild.get_channel(int(campaign.narration_channel_id))
            if ch:
                await ch.send(embed=combat_embed(
                    "Initiative Order",
                    order_str,
                    "Combat begins! Check your private channel for actions.",
                ))

        # Notify each player in their private channel
        for pid in campaign.player_ids:
            ch_id = campaign.player_channel_ids.get(pid)
            if ch_id:
                ch = interaction.guild.get_channel(int(ch_id))
                if ch:
                    char = await db.load_character(pid, guild_id)
                    if char:
                        turn = get_turn_tracking(combat, pid)
                        actions_text = get_available_actions_text(char, turn)
                        await ch.send(embed=info_embed(
                            "⚔️ Combat Started!",
                            f"{actions_text}\n\n"
                            f"Use `/combat_action`, `/combat_attack`, `/combat_cast`, or `/combat_move`.\n"
                            f"When done with your turn: `/combat_end_turn`"
                        ))

        await db.append_log(guild_id, "combat",
            f"Encounter started: {encounter_data.get('name', encounter_name)}")

        # Run monster turns if first
        await self._run_monster_turns(interaction.guild, campaign, combat)

        await interaction.followup.send(
            embed=success_embed(f"Encounter **{encounter_data.get('name', encounter_name)}** started!"),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # /combat_status
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_status", description="Show current combat state")
    async def combat_status(self, interaction: discord.Interaction):
        combat = await db.load_combat(str(interaction.guild_id))
        if not combat or not combat.is_active:
            await interaction.response.send_message(
                embed=error_embed("No active combat."), ephemeral=True
            )
            return
        status = get_combat_status(combat)
        current_id = combat.current_combatant_id()
        current_name = "?"
        if current_id in combat.players:
            current_name = Character.from_dict(combat.players[current_id]).name
        elif current_id in combat.monsters:
            current_name = Monster.from_dict(combat.monsters[current_id]).name
        await interaction.response.send_message(
            embed=combat_status_embed(status, combat.round_number, current_name),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # /combat_action — AI-parsed free-form action
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_action", description="Describe your action in plain English — AI will parse it")
    @app_commands.describe(description="What you want to do, e.g. 'I slash at the goblin with my sword'")
    async def combat_action(self, interaction: discord.Interaction, description: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        campaign, combat = await self._get_campaign_and_combat(guild_id)
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

        # Parse the action with AI
        all_spells = char.cantrips + char.prepared_spells + char.known_spells
        equipped = char.equipped_weapon()
        items = [i.name for i in char.inventory if i.item_type in ("consumable", "weapon")]
        is_rogue = char.char_class.lower() == "rogue"

        action = await parse_player_action(
            player_description=description,
            available_spells=all_spells,
            available_items=items,
            is_rogue=is_rogue,
            context=f"Round {combat.round_number}, Location: {combat.location}",
        )

        action_type = action.get("action_type", "other")
        is_bonus = action.get("is_bonus_action", False)
        economy_type = "bonus_action" if is_bonus else "action"

        turn = get_turn_tracking(combat, discord_id)

        try:
            validate_action_available(turn, economy_type)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        result_text = ""

        # --- ATTACK ---
        if action_type == "attack":
            target_name = action.get("target")
            if not target_name:
                await interaction.followup.send(embed=error_embed("Who are you attacking? Try `/combat_attack target:<name>`"))
                return
            try:
                target_id, target_type = validate_target(combat, target_name)
            except ValidationError as e:
                await interaction.followup.send(embed=error_embed(str(e)))
                return

            if target_type == "monster":
                target = get_monster_from_combat(combat, target_id)
            else:
                target = get_character_from_combat(combat, target_id)

            if not target:
                await interaction.followup.send(embed=error_embed("Target not found."))
                return

            ab = char.ability_scores
            weapon = char.equipped_weapon()
            if weapon:
                dmg = weapon.damage or "1d4"
                dmg_type = weapon.damage_type or "bludgeoning"
                # Use STR for melee, DEX for finesse/ranged
                if "finesse" in (weapon.properties or []):
                    atk_mod = max(ab.str_mod, ab.dex_mod) + char.proficiency_bonus
                elif "ammunition" in str(weapon.properties):
                    atk_mod = ab.dex_mod + char.proficiency_bonus
                else:
                    atk_mod = ab.str_mod + char.proficiency_bonus
            else:
                dmg, dmg_type, atk_mod = "1d4", "bludgeoning", ab.str_mod + char.proficiency_bonus

            from engine.combat_engine import resolve_melee_attack
            result = resolve_melee_attack(char.name, atk_mod, dmg, dmg_type, target)
            combat.add_log(result.description)

            if target_type == "monster":
                save_monster_to_combat(combat, target)
            else:
                save_character_to_combat(combat, target)

            result_text = result.description

        # --- SPELL ---
        elif action_type == "spell":
            spell_name = action.get("spell_name", "")
            slot_level = action.get("spell_slot_level", 0) or 0
            target_name = action.get("target")
            target = None
            if target_name:
                try:
                    target_id, target_type = validate_target(combat, target_name)
                    target = (get_monster_from_combat(combat, target_id) if target_type == "monster"
                              else get_character_from_combat(combat, target_id))
                except ValidationError:
                    pass

            if not spell_name:
                await interaction.followup.send(embed=error_embed("I couldn't determine which spell to cast. Try `/combat_cast spell:<name>`."))
                return

            try:
                validate_spell_slot(char, slot_level)
            except ValidationError as e:
                await interaction.followup.send(embed=error_embed(str(e)))
                return

            result = resolve_spell(char, spell_name, slot_level, target, combat)
            if result.error:
                await interaction.followup.send(embed=error_embed(result.error))
                return

            combat.add_log(result.description)
            if target and isinstance(target, Monster):
                save_monster_to_combat(combat, target)
            elif target and isinstance(target, Character):
                save_character_to_combat(combat, target)
            result_text = result.description

        # --- MOVE ---
        elif action_type == "move":
            feet = action.get("movement_feet") or 30
            try:
                validate_movement(char, turn, feet)
            except ValidationError as e:
                await interaction.followup.send(embed=error_embed(str(e)))
                return
            consume_movement(combat, discord_id, feet)
            result_text = f"**{char.name}** moves {feet} feet."
            combat.add_log(result_text)
            # Movement doesn't consume action
            economy_type = None

        # --- DASH ---
        elif action_type == "dash":
            result_text = f"**{char.name}** Dashes — movement doubled to {char.speed * 2} feet this turn."
            combat.add_log(result_text)

        # --- DODGE ---
        elif action_type == "dodge":
            result_text = f"**{char.name}** takes the Dodge action — attacks against them have disadvantage until next turn."
            combat.add_log(result_text)

        # --- HIDE ---
        elif action_type == "hide":
            from engine.dice import roll_d20
            roll = roll_d20() + char.ability_scores.dex_mod + char.proficiency_bonus
            result_text = f"**{char.name}** attempts to Hide — Stealth: **{roll}**."
            combat.add_log(result_text)

        # --- DISENGAGE ---
        elif action_type == "disengage":
            result_text = f"**{char.name}** Disengages — movement won't provoke opportunity attacks this turn."
            combat.add_log(result_text)

        # --- ITEM ---
        elif action_type == "item":
            item_name = action.get("item_name", "an item")
            result_text = f"**{char.name}** uses **{item_name}**."
            if "potion" in item_name.lower():
                healed, _ = roll_dice("2d4+2")
                char.heal(healed)
                result_text += f" Restores {healed} HP ({char.current_hp}/{char.max_hp} HP)."
            combat.add_log(result_text)

        else:
            result_text = f"**{char.name}**: {description}"
            combat.add_log(result_text)

        # Consume action economy
        if economy_type:
            consume_action(combat, discord_id, economy_type)

        # Save updated char
        save_character_to_combat(combat, char)
        await db.save_character(char, guild_id)
        await db.save_combat(guild_id, combat)

        # AI narration
        narration = await narrate_combat_action(
            action_description=description,
            mechanical_result=result_text,
            context=f"Round {combat.round_number}",
        )
        await self._post_narration(interaction.guild, campaign, narration)
        await db.append_log(guild_id, "combat", result_text)

        # Check for end
        over, reason = is_combat_over(combat)
        if over:
            await self._end_combat(interaction.guild, campaign, combat, reason)
            await interaction.followup.send(embed=info_embed("Action Resolved", result_text))
            return

        turn = get_turn_tracking(combat, discord_id)
        actions_left = get_available_actions_text(char, turn)
        await interaction.followup.send(embed=info_embed("Action Resolved", f"{result_text}\n\n{actions_left}"))

    # ------------------------------------------------------------------
    # /combat_attack — explicit weapon attack
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_attack", description="Make a weapon attack")
    @app_commands.describe(target="Name of the target (e.g. 'goblin', 'goblin_1')")
    async def combat_attack(self, interaction: discord.Interaction, target: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        campaign, combat = await self._get_campaign_and_combat(guild_id)
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
            validate_action_available(turn, "action")
            target_id, target_type = validate_target(combat, target)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        tgt = (get_monster_from_combat(combat, target_id) if target_type == "monster"
               else get_character_from_combat(combat, target_id))
        if not tgt:
            await interaction.followup.send(embed=error_embed("Target not found."))
            return

        ab = char.ability_scores
        weapon = char.equipped_weapon()
        if weapon:
            dmg = weapon.damage or "1d4"
            dmg_type = weapon.damage_type or "bludgeoning"
            if "finesse" in (weapon.properties or []):
                atk_mod = max(ab.str_mod, ab.dex_mod) + char.proficiency_bonus
            elif "ammunition" in str(weapon.properties):
                atk_mod = ab.dex_mod + char.proficiency_bonus
            else:
                atk_mod = ab.str_mod + char.proficiency_bonus
        else:
            dmg, dmg_type, atk_mod = "1d4", "bludgeoning", ab.str_mod + char.proficiency_bonus

        result = resolve_melee_attack(char.name, atk_mod, dmg, dmg_type, tgt)
        combat.add_log(result.description)

        if target_type == "monster":
            save_monster_to_combat(combat, tgt)
        else:
            save_character_to_combat(combat, tgt)

        consume_action(combat, discord_id, "action")
        save_character_to_combat(combat, char)
        await db.save_combat(guild_id, combat)
        await db.append_log(guild_id, "combat", result.description)

        narration = await narrate_combat_action(
            action_description=f"{char.name} attacks {tgt.name}",
            mechanical_result=result.description,
        )
        await self._post_narration(interaction.guild, campaign, narration)

        over, reason = is_combat_over(combat)
        if over:
            await self._end_combat(interaction.guild, campaign, combat, reason)

        turn = get_turn_tracking(combat, discord_id)
        await interaction.followup.send(embed=info_embed(
            "⚔️ Attack",
            f"{result.description}\n\n{get_available_actions_text(char, turn)}"
        ))

    # ------------------------------------------------------------------
    # /combat_cast — cast a spell
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_cast", description="Cast a spell")
    @app_commands.describe(
        spell="Spell name (e.g. 'fire bolt', 'cure wounds')",
        target="Target name (optional)",
        slot="Spell slot level (0 for cantrips, default 1)",
    )
    async def combat_cast(
        self, interaction: discord.Interaction,
        spell: str, target: str = "", slot: int = 1
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        campaign, combat = await self._get_campaign_and_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.followup.send(embed=error_embed("No character found."))
            return

        from data.campaign.spells import get_spell
        spell_data = get_spell(spell.lower())
        if not spell_data:
            await interaction.followup.send(embed=error_embed(f"Unknown spell: `{spell}`"))
            return

        action_type = spell_data.get("action_type", "action")

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, action_type)
            validate_spell_slot(char, slot if slot > 0 else 0)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        if not validate_spell_known(char, spell):
            await interaction.followup.send(embed=error_embed(
                f"You don't know the spell **{spell}**. Check `/character_spells`."
            ))
            return

        tgt = None
        if target:
            try:
                target_id, target_type = validate_target(combat, target)
                tgt = (get_monster_from_combat(combat, target_id) if target_type == "monster"
                       else get_character_from_combat(combat, target_id))
            except ValidationError as e:
                await interaction.followup.send(embed=error_embed(str(e)))
                return

        result = resolve_spell(char, spell, slot if slot > 0 else 0, tgt, combat)
        if result.error:
            await interaction.followup.send(embed=error_embed(result.error))
            return

        combat.add_log(result.description)
        if tgt and isinstance(tgt, Monster):
            save_monster_to_combat(combat, tgt)
        elif tgt and isinstance(tgt, Character):
            save_character_to_combat(combat, tgt)

        consume_action(combat, discord_id, action_type)
        save_character_to_combat(combat, char)
        await db.save_character(char, guild_id)
        await db.save_combat(guild_id, combat)
        await db.append_log(guild_id, "combat", result.description)

        narration = await narrate_combat_action(
            action_description=f"{char.name} casts {spell}",
            mechanical_result=result.description,
        )
        await self._post_narration(interaction.guild, campaign, narration)

        over, reason = is_combat_over(combat)
        if over:
            await self._end_combat(interaction.guild, campaign, combat, reason)

        turn = get_turn_tracking(combat, discord_id)
        await interaction.followup.send(embed=info_embed(
            f"✨ {spell_data['name']}",
            f"{result.description}\n\n{get_available_actions_text(char, turn)}"
        ))

    # ------------------------------------------------------------------
    # /combat_move
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_move", description="Move your character (uses movement speed)")
    @app_commands.describe(feet="How many feet to move (max is your speed)")
    async def combat_move(self, interaction: discord.Interaction, feet: int):
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.response.send_message(embed=error_embed("No active combat."), ephemeral=True)
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_movement(char, turn, feet)
        except ValidationError as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return

        consume_movement(combat, discord_id, feet)
        await db.save_combat(guild_id, combat)

        remaining = char.speed - get_turn_tracking(combat, discord_id).movement_used
        await interaction.response.send_message(
            embed=success_embed(f"**{char.name}** moves {feet} feet. ({remaining} ft remaining)"),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # /combat_dash
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_dash", description="Dash — use your action to double movement this turn")
    async def combat_dash(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.response.send_message(embed=error_embed("No active combat."), ephemeral=True)
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, "action")
        except ValidationError as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return

        consume_action(combat, discord_id, "action")
        await db.save_combat(guild_id, combat)
        await interaction.response.send_message(
            embed=success_embed(f"**{char.name}** Dashes! Movement is doubled to {char.speed * 2} ft this turn."),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # /combat_dodge
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_dodge", description="Dodge — attacks against you have disadvantage until your next turn")
    async def combat_dodge(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.response.send_message(embed=error_embed("No active combat."), ephemeral=True)
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
            turn = get_turn_tracking(combat, discord_id)
            validate_action_available(turn, "action")
        except ValidationError as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return

        consume_action(combat, discord_id, "action")
        if "dodging" not in char.conditions:
            char.conditions.append("dodging")
        save_character_to_combat(combat, char)
        await db.save_character(char, guild_id)
        await db.save_combat(guild_id, combat)

        await interaction.response.send_message(
            embed=success_embed(f"**{char.name}** takes the Dodge action. Attacks against you have disadvantage until your next turn."),
            ephemeral=True,
        )

    # ------------------------------------------------------------------
    # /combat_end_turn
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_end_turn", description="End your turn and advance to the next combatant")
    async def combat_end_turn(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        campaign, combat = await self._get_campaign_and_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.followup.send(embed=error_embed("No active combat."))
            return

        try:
            validate_it_is_your_turn(combat, discord_id)
        except ValidationError as e:
            await interaction.followup.send(embed=error_embed(str(e)))
            return

        # Remove dodge condition at end of turn
        char = await db.load_character(discord_id, guild_id)
        if char and "dodging" in char.conditions:
            char.conditions.remove("dodging")
            save_character_to_combat(combat, char)
            await db.save_character(char, guild_id)

        combat.advance_turn()
        await db.save_combat(guild_id, combat)

        await interaction.followup.send(embed=success_embed("Turn ended."))

        # Run any consecutive monster turns
        await self._run_monster_turns(interaction.guild, campaign, combat)

    # ------------------------------------------------------------------
    # /combat_death_save
    # ------------------------------------------------------------------

    @app_commands.command(name="combat_death_save", description="Make a death saving throw (when at 0 HP)")
    async def combat_death_save(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        discord_id = str(interaction.user.id)

        combat = await db.load_combat(guild_id)
        if not combat or not combat.is_active:
            await interaction.response.send_message(embed=error_embed("No active combat."), ephemeral=True)
            return

        char = await db.load_character(discord_id, guild_id)
        if not char:
            await interaction.response.send_message(embed=error_embed("No character found."), ephemeral=True)
            return

        if char.current_hp > 0:
            await interaction.response.send_message(
                embed=error_embed("You still have HP — death saves are only for when you're at 0 HP."),
                ephemeral=True,
            )
            return

        result = make_death_save(char)
        save_character_to_combat(combat, char)
        await db.save_character(char, guild_id)
        await db.save_combat(guild_id, combat)

        campaign = await db.load_campaign(guild_id)
        if "stabilized" in result.events or "dead" in result.events:
            await self._post_narration(interaction.guild, campaign, result.description)

        await interaction.response.send_message(embed=info_embed("💀 Death Save", result.description), ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
