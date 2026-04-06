"""
Discord UI Views — persistent buttons and modals for in-combat
and out-of-combat player actions.

All views use stable custom_id patterns so they survive bot restarts.
State is always loaded fresh from the database on each interaction.
"""
from __future__ import annotations
import discord
from discord import ui
from typing import TYPE_CHECKING


# ---------------------------------------------------------------------------
# Character Creation
# ---------------------------------------------------------------------------

class CharacterCreationModal(ui.Modal, title="Create Your Character"):
    char_name = ui.TextInput(
        label="Character name",
        placeholder="e.g. Thorin, Lyra, Kael",
        min_length=1, max_length=32,
    )
    race = ui.TextInput(
        label="Race",
        placeholder="Human / Elf / Dwarf / Halfling / Half-Elf / Half-Orc / Gnome / Dragonborn / Tiefling",
        min_length=2, max_length=20,
    )
    char_class = ui.TextInput(
        label="Class",
        placeholder="Fighter / Wizard / Rogue / Cleric / Ranger / Paladin / Barbarian / Bard",
        min_length=3, max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("CharacterCog")
        if not cog:
            await interaction.followup.send("Character system unavailable.", ephemeral=True)
            return
        await cog._do_character_creation(
            interaction,
            name=self.char_name.value.strip(),
            race=self.race.value.strip(),
            char_class=self.char_class.value.strip(),
        )


class CharacterCreationView(ui.View):
    """
    Posted in the player's private channel at game start.
    Shows a single 'Create Character' button that opens the creation modal.
    Persistent so it survives bot restarts.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="✨ Begin Character Creation",
        style=discord.ButtonStyle.success,
        custom_id="dnd_create_character",
        row=0,
    )
    async def create_character(self, interaction: discord.Interaction, button: ui.Button):
        # Only show the modal if they don't already have a character
        import data.database as db
        char = await db.load_character(str(interaction.user.id), str(interaction.guild_id))
        if char:
            await interaction.response.send_message(
                f"You already have a character — **{char.name}** the {char.race} {char.char_class}!\n"
                "Use the exploration buttons in your channel or `/character_sheet` to view your sheet.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(CharacterCreationModal())


# ---------------------------------------------------------------------------
# Modals
# ---------------------------------------------------------------------------

class AttackModal(ui.Modal, title="Attack"):
    target = ui.TextInput(
        label="Target name",
        placeholder="e.g. goblin, goblin_1, bugbear",
        min_length=1, max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_attack.callback(cog, interaction, target=self.target.value)
        else:
            await interaction.response.send_message("Combat system unavailable.", ephemeral=True)


class CastSpellModal(ui.Modal, title="Cast a Spell"):
    spell = ui.TextInput(
        label="Spell name",
        placeholder="e.g. fire bolt, cure wounds, magic missile",
        min_length=1, max_length=50,
    )
    target = ui.TextInput(
        label="Target (leave blank for self/area spells)",
        placeholder="e.g. goblin_1, Thorin",
        required=False, max_length=50,
    )
    slot = ui.TextInput(
        label="Spell slot level (0 = cantrip)",
        placeholder="1",
        default="1", min_length=1, max_length=1,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            try:
                slot_level = int(self.slot.value)
            except ValueError:
                slot_level = 1
            await cog.combat_cast.callback(
                cog, interaction,
                spell=self.spell.value,
                target=self.target.value or "",
                slot=slot_level,
            )
        else:
            await interaction.response.send_message("Combat system unavailable.", ephemeral=True)


class MoveModal(ui.Modal, title="Move"):
    feet = ui.TextInput(
        label="How many feet to move?",
        placeholder="e.g. 30",
        default="30", min_length=1, max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            try:
                ft = int(self.feet.value)
            except ValueError:
                ft = 30
            await cog.combat_move.callback(cog, interaction, feet=ft)
        else:
            await interaction.response.send_message("Combat system unavailable.", ephemeral=True)


class FreeActionModal(ui.Modal, title="Describe your action"):
    description = ui.TextInput(
        label="What do you do?",
        placeholder="e.g. I shove the goblin away and draw my sword",
        style=discord.TextStyle.paragraph,
        min_length=2, max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_action.callback(cog, interaction, description=self.description.value)
        else:
            await interaction.response.send_message("Combat system unavailable.", ephemeral=True)


class SkillCheckModal(ui.Modal, title="Skill Check"):
    skill = ui.TextInput(
        label="Skill",
        placeholder="e.g. perception, stealth, persuasion",
        min_length=2, max_length=30,
    )
    description = ui.TextInput(
        label="What are you trying to do?",
        placeholder="e.g. Listen for movement behind the door",
        style=discord.TextStyle.paragraph,
        min_length=2, max_length=200,
    )
    dc = ui.TextInput(
        label="DC (optional — leave blank if unknown)",
        placeholder="e.g. 12",
        required=False, max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            try:
                dc_val = int(self.dc.value) if self.dc.value.strip() else 0
            except ValueError:
                dc_val = 0
            await cog.action_skill.callback(
                cog, interaction,
                skill=self.skill.value,
                description=self.description.value,
                dc=dc_val,
            )
        else:
            await interaction.response.send_message("Actions system unavailable.", ephemeral=True)


class TalkModal(ui.Modal, title="Talk to NPC"):
    npc = ui.TextInput(
        label="NPC name",
        placeholder="e.g. Sildar, Gundren, Toblen",
        min_length=1, max_length=50,
    )
    message = ui.TextInput(
        label="What do you say?",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. Do you know where Gundren was taken?",
        min_length=1, max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_talk.callback(cog, interaction, npc=self.npc.value, message=self.message.value)
        else:
            await interaction.response.send_message("Actions system unavailable.", ephemeral=True)


class FreeExploreModal(ui.Modal, title="Describe your action"):
    description = ui.TextInput(
        label="What do you do?",
        placeholder="e.g. I pick the lock on the chest",
        style=discord.TextStyle.paragraph,
        min_length=2, max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_do.callback(cog, interaction, description=self.description.value)
        else:
            await interaction.response.send_message("Actions system unavailable.", ephemeral=True)


class ExamineModal(ui.Modal, title="Examine"):
    target = ui.TextInput(
        label="What do you examine?",
        placeholder="e.g. the locked chest, the dead goblin, the runes on the wall",
        min_length=1, max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_examine.callback(cog, interaction, target=self.target.value)
        else:
            await interaction.response.send_message("Actions system unavailable.", ephemeral=True)


# ---------------------------------------------------------------------------
# Combat View — posted to player's private channel when it's their turn
# ---------------------------------------------------------------------------

class CombatView(ui.View):
    """
    Buttons for in-combat actions. Posted when it's the player's turn.
    Uses stable custom_ids so it survives bot restarts.
    """

    def __init__(self, is_unconscious: bool = False):
        super().__init__(timeout=None)
        # Hide most buttons if unconscious — only death save shown
        if is_unconscious:
            self.clear_items()
            self.add_item(self._make_death_save_button())

    def _make_death_save_button(self):
        btn = ui.Button(
            label="💀 Death Save",
            style=discord.ButtonStyle.danger,
            custom_id="dnd_death_save",
            row=0,
        )
        btn.callback = self._death_save
        return btn

    # Row 0 — Primary attack actions
    @ui.button(label="⚔️ Attack", style=discord.ButtonStyle.danger,
               custom_id="dnd_attack", row=0)
    async def attack(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AttackModal())

    @ui.button(label="✨ Cast Spell", style=discord.ButtonStyle.primary,
               custom_id="dnd_cast", row=0)
    async def cast_spell(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CastSpellModal())

    @ui.button(label="🎲 Free Action", style=discord.ButtonStyle.secondary,
               custom_id="dnd_free_action", row=0)
    async def free_action(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FreeActionModal())

    # Row 1 — Movement
    @ui.button(label="👟 Move", style=discord.ButtonStyle.secondary,
               custom_id="dnd_move", row=1)
    async def move(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MoveModal())

    @ui.button(label="💨 Dash", style=discord.ButtonStyle.secondary,
               custom_id="dnd_dash", row=1)
    async def dash(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_dash.callback(cog, interaction)

    @ui.button(label="🗺️ Disengage", style=discord.ButtonStyle.secondary,
               custom_id="dnd_disengage", row=1)
    async def disengage(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_disengage.callback(cog, interaction)

    # Row 2 — Defensive / utility
    @ui.button(label="🛡️ Dodge", style=discord.ButtonStyle.secondary,
               custom_id="dnd_dodge", row=2)
    async def dodge(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_dodge.callback(cog, interaction)

    @ui.button(label="🤫 Hide", style=discord.ButtonStyle.secondary,
               custom_id="dnd_hide", row=2)
    async def hide(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_hide.callback(cog, interaction)

    @ui.button(label="🤝 Help", style=discord.ButtonStyle.secondary,
               custom_id="dnd_help_action", row=2)
    async def help_action(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_help_action.callback(cog, interaction)

    @ui.button(label="🧪 Use Potion", style=discord.ButtonStyle.success,
               custom_id="dnd_potion", row=2)
    async def use_potion(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_use_potion.callback(cog, interaction)

    # Row 3 — Turn management
    @ui.button(label="📊 Status", style=discord.ButtonStyle.secondary,
               custom_id="dnd_status_btn", row=3)
    async def status(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_status.callback(cog, interaction)

    @ui.button(label="🎯 My Actions", style=discord.ButtonStyle.secondary,
               custom_id="dnd_my_actions", row=3)
    async def my_actions(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_actions.callback(cog, interaction)

    @ui.button(label="⏭️ End Turn", style=discord.ButtonStyle.success,
               custom_id="dnd_end_turn", row=3)
    async def end_turn(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_end_turn.callback(cog, interaction)

    async def _death_save(self, interaction: discord.Interaction):
        from cogs.combat_cog import CombatCog
        cog = interaction.client.get_cog("CombatCog")
        if cog:
            await cog.combat_death_save.callback(cog, interaction)


# ---------------------------------------------------------------------------
# Exploration View — always available in player's private channel
# ---------------------------------------------------------------------------

class ExplorationView(ui.View):
    """
    Buttons for out-of-combat exploration actions.
    Persistent — re-posted to player channels and re-registered on startup.
    """

    def __init__(self):
        super().__init__(timeout=None)

    # Row 0 — Exploration
    @ui.button(label="👁️ Look Around", style=discord.ButtonStyle.primary,
               custom_id="dnd_look", row=0)
    async def look(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_look.callback(cog, interaction)

    @ui.button(label="🔍 Search Area", style=discord.ButtonStyle.primary,
               custom_id="dnd_search", row=0)
    async def search(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_search.callback(cog, interaction)

    @ui.button(label="🔎 Examine", style=discord.ButtonStyle.primary,
               custom_id="dnd_examine", row=0)
    async def examine(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ExamineModal())

    @ui.button(label="🎲 Skill Check", style=discord.ButtonStyle.primary,
               custom_id="dnd_skill", row=0)
    async def skill_check(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SkillCheckModal())

    # Row 1 — Social / narrative
    @ui.button(label="💬 Talk to NPC", style=discord.ButtonStyle.secondary,
               custom_id="dnd_talk", row=1)
    async def talk(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TalkModal())

    @ui.button(label="🤫 Sneak", style=discord.ButtonStyle.secondary,
               custom_id="dnd_sneak", row=1)
    async def sneak(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_sneak.callback(cog, interaction)

    @ui.button(label="⚡ Do Something", style=discord.ButtonStyle.secondary,
               custom_id="dnd_do", row=1)
    async def do_action(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FreeExploreModal())

    # Row 2 — Character info
    @ui.button(label="📜 Character Sheet", style=discord.ButtonStyle.secondary,
               custom_id="dnd_sheet", row=2)
    async def sheet(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_sheet.callback(cog, interaction)

    @ui.button(label="🎒 Inventory", style=discord.ButtonStyle.secondary,
               custom_id="dnd_inventory", row=2)
    async def inventory(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_inventory.callback(cog, interaction)

    @ui.button(label="✨ Spells", style=discord.ButtonStyle.secondary,
               custom_id="dnd_spells", row=2)
    async def spells(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_spells.callback(cog, interaction)

    # Row 3 — Rest & quests
    @ui.button(label="😴 Short Rest", style=discord.ButtonStyle.success,
               custom_id="dnd_short_rest", row=3)
    async def short_rest(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_rest.callback(cog, interaction, rest_type="short")

    @ui.button(label="🌙 Long Rest", style=discord.ButtonStyle.success,
               custom_id="dnd_long_rest", row=3)
    async def long_rest(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.character_cog import CharacterCog
        cog = interaction.client.get_cog("CharacterCog")
        if cog:
            await cog.character_rest.callback(cog, interaction, rest_type="long")

    @ui.button(label="📋 Quests", style=discord.ButtonStyle.secondary,
               custom_id="dnd_quests", row=3)
    async def quests(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.game_cog import GameCog
        cog = interaction.client.get_cog("GameCog")
        if cog:
            await cog.quest_list.callback(cog, interaction)

    @ui.button(label="💰 Loot", style=discord.ButtonStyle.secondary,
               custom_id="dnd_loot_btn", row=3)
    async def loot(self, interaction: discord.Interaction, button: ui.Button):
        from cogs.actions_cog import ActionsCog
        cog = interaction.client.get_cog("ActionsCog")
        if cog:
            await cog.action_loot.callback(cog, interaction)


# ---------------------------------------------------------------------------
# Helper: build the right view for a given player state
# ---------------------------------------------------------------------------

def build_player_view(in_combat: bool, is_unconscious: bool = False) -> ui.View:
    if in_combat:
        return CombatView(is_unconscious=is_unconscious)
    return ExplorationView()
