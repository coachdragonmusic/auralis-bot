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
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

UPDATE_CHANNEL_NAME = "song-updates"
COLLAB_CATEGORY_NAME = "📢 Collaboration"

COLLABORATORS = [
    "CoachDragon",
    "mizuki17"
]


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def clean_channel_name(title: str) -> str:
    name = title.lower().strip()
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    return name[:80]


def clean_song_category_name(category_name: str) -> str:
    name = category_name.replace("🎵", "").strip()
    return clean_channel_name(name)


def is_song_category(category: discord.CategoryChannel) -> bool:
    if category.name.startswith("🎵"):
        return True

    song_channel_keywords = [
        "lyrics",
        "prompts",
        "revisions",
        "mixing-notes",
        "song-demos",
        "final-exports"
    ]

    channel_names = [channel.name for channel in category.channels]

    matches = 0

    for channel_name in channel_names:
        for keyword in song_channel_keywords:
            if keyword in channel_name:
                matches += 1
                break

    return matches >= 2


async def get_or_create_update_channel(guild: discord.Guild):
    update_channel = discord.utils.get(
        guild.text_channels,
        name=UPDATE_CHANNEL_NAME
    )

    if update_channel is not None:
        return update_channel

    collaboration_category = discord.utils.get(
        guild.categories,
        name=COLLAB_CATEGORY_NAME
    )

    if collaboration_category is None:
        collaboration_category = await guild.create_category(
            COLLAB_CATEGORY_NAME
        )

    update_channel = await guild.create_text_channel(
        UPDATE_CHANNEL_NAME,
        category=collaboration_category
    )

    return update_channel


def find_collaborators_to_notify(
    guild: discord.Guild,
    author: discord.Member
):
    members_to_notify = []

    for member in guild.members:

        if member.bot:
            continue

        if member.id == author.id:
            continue

        for collaborator in COLLABORATORS:

            username = collaborator.lower().replace("@", "")

            matched = False

            if member.name and member.name.lower() == username:
                matched = True

            if member.display_name and member.display_name.lower() == username:
                matched = True

            if member.global_name and member.global_name.lower() == username:
                matched = True

            if matched:
                members_to_notify.append(member)
                break

    return members_to_notify


# ─────────────────────────────────────────────
# Bot Ready Event
# ─────────────────────────────────────────────

@client.event
async def on_ready():
    await tree.sync()
    print(f"Auralis is online as {client.user}")


# ─────────────────────────────────────────────
# Clean Collaboration Message System
# ─────────────────────────────────────────────

@client.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    if not message.content.startswith("n "):
        return

    update_text = message.content[2:].strip()

    if not update_text:
        return

    update_channel = await get_or_create_update_channel(
        message.guild
    )

    # ─────────────────────────────────────────
    # Delete Original Raw Message
    # ─────────────────────────────────────────

    try:
        await message.delete()
    except Exception as error:
        print(f"Failed to delete message: {error}")

    # ─────────────────────────────────────────
    # Repost Clean Message As Bot
    # ─────────────────────────────────────────

    try:
        await message.channel.send(update_text)
    except Exception as error:
        print(f"Failed to repost message: {error}")

    # ─────────────────────────────────────────
    # Determine Collaborators To Notify
    # ─────────────────────────────────────────

    notify_members = find_collaborators_to_notify(
        message.guild,
        message.author
    )

    mention_text = " ".join(
        [member.mention for member in notify_members]
    )

    # ─────────────────────────────────────────
    # Build Update Embed
    # ─────────────────────────────────────────

    now = discord.utils.utcnow()

    embed = discord.Embed(
        title="🔔 New Song Update",
        description=update_text,
        color=0x00FF7F
    )

    embed.add_field(
        name="Channel",
        value=message.channel.mention,
        inline=True
    )

    embed.add_field(
        name="Updated By",
        value=message.author.mention,
        inline=True
    )

    embed.add_field(
        name="Time",
        value=discord.utils.format_dt(now, style="F"),
        inline=False
    )

    embed.set_footer(
        text="Auralis • Song Collaboration Log"
    )

    # ─────────────────────────────────────────
    # Send Update Log
    # ─────────────────────────────────────────

    await update_channel.send(
        content=mention_text,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            everyone=False,
            users=True,
            roles=False
        )
    )


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

    await interaction.response.send_message(
        f"Creating project for **{title}**...",
        ephemeral=True
    )

    clean_name = clean_channel_name(title)

    category = await guild.create_category(
        f"🎵 {title}"
    )

    channels = [
        f"{clean_name}-lyrics",
        f"{clean_name}-prompts",
        f"{clean_name}-revisions",
        f"{clean_name}-mixing-notes",
        f"{clean_name}-song-demos",
        f"{clean_name}-final-exports"
    ]

    for channel_name in channels:
        await guild.create_text_channel(
            channel_name,
            category=category
        )


# ─────────────────────────────────────────────
# /add_demos_channels Command
# ─────────────────────────────────────────────

@tree.command(
    name="add_demos_channels",
    description="Add missing song-demos channels to existing song categories."
)
async def add_demos_channels(interaction: discord.Interaction):

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

    await interaction.response.send_message(
        "Scanning song categories...",
        ephemeral=True
    )

    added_channels = []

    for category in guild.categories:

        if not is_song_category(category):
            continue

        clean_name = clean_song_category_name(
            category.name
        )

        demo_channel_name = (
            f"{clean_name}-song-demos"
        )

        existing_channel = discord.utils.get(
            category.channels,
            name=demo_channel_name
        )

        if existing_channel is not None:
            continue

        await guild.create_text_channel(
            demo_channel_name,
            category=category
        )

        added_channels.append(
            f"{category.name} → #{demo_channel_name}"
        )

    if added_channels:

        added_text = "\n".join(
            [f"• {item}" for item in added_channels]
        )

        embed = discord.Embed(
            title="Song Demo Channels Added",
            description=added_text,
            color=0x00FF7F
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    else:

        await interaction.followup.send(
            "No missing demo channels found.",
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

    async def callback(self, interaction):

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
            f"Deleting **{category.name}**...",
            ephemeral=True
        )

        for channel in list(category.channels):
            await channel.delete()

        await category.delete()


class CategoryDeleteView(discord.ui.View):

    def __init__(self, categories):
        super().__init__(timeout=300)
        self.add_item(
            CategoryDeleteSelect(categories)
        )


# ─────────────────────────────────────────────
# /clean_categories Command
# ─────────────────────────────────────────────

@tree.command(
    name="clean_categories",
    description="Delete a category and all channels."
)
async def clean_categories(interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command only works in a server.",
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
        "Pick the category to delete:",
        view=view,
        ephemeral=True
    )


# ─────────────────────────────────────────────
# Multi Channel Delete Dropdown
# ─────────────────────────────────────────────

class ChannelDeleteSelect(discord.ui.Select):

    def __init__(self, channels):

        options = [
            discord.SelectOption(
                label=channel.name[:100],
                value=str(channel.id)
            )
            for channel in channels[:25]
        ]

        super().__init__(
            placeholder="Choose channels to delete...",
            min_values=1,
            max_values=min(len(options), 25),
            options=options
        )

    async def callback(self, interaction):

        await interaction.response.send_message(
            "Deleting selected channels...",
            ephemeral=True
        )

        for value in self.values:

            channel_id = int(value)

            channel = discord.utils.get(
                interaction.guild.text_channels,
                id=channel_id
            )

            if channel is not None:

                try:
                    await channel.delete()
                except Exception as error:
                    print(error)


class ChannelDeleteView(discord.ui.View):

    def __init__(self, channels):
        super().__init__(timeout=300)
        self.add_item(
            ChannelDeleteSelect(channels)
        )


# ─────────────────────────────────────────────
# /clean_channels Command
# ─────────────────────────────────────────────

@tree.command(
    name="clean_channels",
    description="Delete multiple channels."
)
async def clean_channels(interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command only works in a server.",
            ephemeral=True
        )
        return

    channels = guild.text_channels

    if not channels:
        await interaction.response.send_message(
            "No text channels found.",
            ephemeral=True
        )
        return

    view = ChannelDeleteView(channels)

    await interaction.response.send_message(
        "Pick channels to delete:",
        view=view,
        ephemeral=True
    )


# ─────────────────────────────────────────────
# /help Command
# ─────────────────────────────────────────────

@tree.command(
    name="help",
    description="Show Auralis command list."
)
async def help_command(interaction):

    embed = discord.Embed(
        title="Auralis Commands",
        description=(
            "Organization and collaboration "
            "tools for songwriting."
        ),
        color=0x00FF7F
    )

    embed.add_field(
        name="/newsong",
        value="Create a full song project.",
        inline=False
    )

    embed.add_field(
        name="/add_demos_channels",
        value=(
            "Add missing song-demos "
            "channels to old projects."
        ),
        inline=False
    )

    embed.add_field(
        name="/clean_channels",
        value="Delete multiple channels.",
        inline=False
    )

    embed.add_field(
        name="/clean_categories",
        value="Delete entire categories.",
        inline=False
    )

    embed.add_field(
        name="n your message",
        value=(
            "Clean collaboration update "
            "system with automatic tagging."
        ),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ─────────────────────────────────────────────
# Run Bot
# ─────────────────────────────────────────────

client.run(TOKEN)
