import os
import re
import discord
from discord import app_commands
from dotenv import load_dotenv


# ─────────────────────────────────────────────
# Load Environment Variables
# ─────────────────────────────────────────────

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


# ─────────────────────────────────────────────
# Discord Setup
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def clean_channel_name(title: str) -> str:
    name = title.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return name[:80]


# ─────────────────────────────────────────────
# Bot Ready Event
# ─────────────────────────────────────────────

@client.event
async def on_ready():
    await tree.sync()
    print(f"Auralis is online as {client.user}")


# ─────────────────────────────────────────────
# /newsong Command
# ─────────────────────────────────────────────

@tree.command(
    name="newsong",
    description="Create a new organized song project."
)
@app_commands.describe(title="Song title")
async def newsong(interaction: discord.Interaction, title: str):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command only works in a server.",
            ephemeral=True
        )
        return

    clean_name = clean_channel_name(title)

    category = await guild.create_category(
        f"🎵 {title}"
    )

    channels = [
        f"{clean_name}-lyrics",
        f"{clean_name}-prompts",
        f"{clean_name}-revisions",
        f"{clean_name}-mixing-notes",
        f"{clean_name}-final-exports"
    ]

    for channel_name in channels:
        await guild.create_text_channel(
            channel_name,
            category=category
        )

    await interaction.response.send_message(
        f"Created project for **{title}**.",
        ephemeral=True
    )


# ─────────────────────────────────────────────
# Category Delete Dropdown
# ─────────────────────────────────────────────

class CategoryDeleteSelect(discord.ui.Select):
    def __init__(self, categories):
        options = [
            discord.SelectOption(
                label=category.name[:100],
                value=str(category.id)
            )
            for category in categories[:25]
        ]

        super().__init__(
            placeholder="Choose a category to delete...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category_id = int(self.values[0])
        category = discord.utils.get(
            interaction.guild.categories,
            id=category_id
        )

        if category is None:
            await interaction.response.send_message(
                "That category no longer exists.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Deleting **{category.name}** and all channels inside it...",
            ephemeral=True
        )

        for channel in category.channels:
            await channel.delete(
                reason=f"Deleted by {interaction.user}"
            )

        await category.delete(
            reason=f"Deleted by {interaction.user}"
        )


class CategoryDeleteView(discord.ui.View):
    def __init__(self, categories):
        super().__init__(timeout=60)
        self.add_item(CategoryDeleteSelect(categories))


# ─────────────────────────────────────────────
# /clean_categories Command
# ─────────────────────────────────────────────

@tree.command(
    name="clean_categories",
    description="Choose a category from a dropdown and delete it."
)
async def clean_categories(interaction: discord.Interaction):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command only works in a server.",
            ephemeral=True
        )
        return

    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            "You need Manage Channels permission to use this.",
            ephemeral=True
        )
        return

    categories = guild.categories

    if not categories:
        await interaction.response.send_message(
            "No categories found.",
            ephemeral=True
        )
        return

    view = CategoryDeleteView(categories)

    await interaction.response.send_message(
        "Pick the category you want to delete:",
        view=view,
        ephemeral=True
    )


# ─────────────────────────────────────────────
# Run Bot
# ─────────────────────────────────────────────

client.run(TOKEN)
