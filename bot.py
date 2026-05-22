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
AURALIS_UPDATE_CHANNEL = "auralis-update-log"

BOT_VERSION = "1.1"

BOT_UPDATE_NOTES = [
    "Initial Auralis release.",
    "Added /newsong for organized song project creation.",
    "Added /clean_channels for bulk channel cleanup.",
    "Added /clean_categories for category cleanup.",
    "Added N/n collaboration updates.",
    "Added automatic collaborator tagging.",
    "Added #song-updates logging.",
    "Added song-demos channels.",
    "Added /add_demos_channels for older song projects.",
    "Added automatic demo upload tracking for MP3, WAV, M4A, FLAC, and OGG files.",
    "Added #auralis-update-log deployment logging.",
    "Added clean author-attributed update reposting.",
]

COLLABORATORS = [
    "CoachDragon",
    "mizuki17"
]

UPDATE_NOTIFY_USERS = [
    "mizuki17"
]

AUDIO_EXTENSIONS = [
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".ogg"
]

startup_log_posted = False


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


def get_song_name_from_channel(channel_name: str) -> str:
    name = channel_name.replace("-song-demos", "")
    name = name.replace("-", " ")
    return name.title()


def is_audio_file(filename: str) -> bool:
    lowered = filename.lower()
    return any(lowered.endswith(ext) for ext in AUDIO_EXTENSIONS)


def is_song_category(category: discord.CategoryChannel) -> bool:
    if category.name.startswith("🎵"):
        return True

    keywords = [
        "lyrics",
        "prompts",
        "revisions",
        "mixing-notes",
        "song-demos",
        "final-exports"
    ]

    matches = 0

    for channel in category.channels:
        for keyword in keywords:
            if keyword in channel.name:
                matches += 1
                break

    return matches >= 2


async def get_or_create_update_channel(guild: discord.Guild):
    channel = discord.utils.get(
        guild.text_channels,
        name=UPDATE_CHANNEL_NAME
    )

    if channel is not None:
        return channel

    category = discord.utils.get(
        guild.categories,
        name=COLLAB_CATEGORY_NAME
    )

    if category is None:
        category = await guild.create_category(
            COLLAB_CATEGORY_NAME
        )

    return await guild.create_text_channel(
        UPDATE_CHANNEL_NAME,
        category=category
    )


async def get_or_create_auralis_update_channel(guild: discord.Guild):
    channel = discord.utils.get(
        guild.text_channels,
        name=AURALIS_UPDATE_CHANNEL
    )

    if channel is not None:
        return channel

    return await guild.create_text_channel(
        AURALIS_UPDATE_CHANNEL
    )


def find_members_by_names(guild: discord.Guild, names: list[str]):
    found_members = []

    for member in guild.members:
        if member.bot:
            continue

        for username in names:
            clean_name = username.lower().replace("@", "")

            matched = False

            if member.name and member.name.lower() == clean_name:
                matched = True

            if member.display_name and member.display_name.lower() == clean_name:
                matched = True

            if member.global_name and member.global_name.lower() == clean_name:
                matched = True

            if matched:
                found_members.append(member)
                break

    return found_members


def find_collaborators_to_notify(
    guild: discord.Guild,
    author: discord.Member
):
    members = find_members_by_names(guild, COLLABORATORS)

    return [
        member for member in members
        if member.id != author.id
    ]


def build_mentions(
    guild: discord.Guild,
    author: discord.Member
):
    notify_members = find_collaborators_to_notify(
        guild,
        author
    )

    return " ".join(
        [member.mention for member in notify_members]
    )


def build_update_log_mentions(guild: discord.Guild):
    notify_members = find_members_by_names(
        guild,
        UPDATE_NOTIFY_USERS
    )

    return " ".join(
        list(set(member.mention for member in notify_members))
    )


async def version_already_logged(
    channel: discord.TextChannel,
    version: str
):
    async for old_message in channel.history(limit=50):
        if old_message.author != client.user:
            continue

        for embed in old_message.embeds:
            for field in embed.fields:
                if field.name == "Version" and field.value == version:
                    return True

    return False


# ─────────────────────────────────────────────
# Bot Ready Event
# ─────────────────────────────────────────────

@client.event
async def on_ready():
    global startup_log_posted

    await tree.sync()

    print(f"Auralis is online as {client.user}")

    if startup_log_posted:
        return

    startup_log_posted = True

    for guild in client.guilds:
        update_channel = await get_or_create_auralis_update_channel(guild)

        if await version_already_logged(update_channel, BOT_VERSION):
            continue

        notes_text = "\n".join(
            [f"• {note}" for note in BOT_UPDATE_NOTES]
        )

        embed = discord.Embed(
            title="🚀 Auralis Updated",
            description="Auralis is online with the latest stable release.",
            color=0x00FF7F
        )

        embed.add_field(
            name="Version",
            value=BOT_VERSION,
            inline=True
        )

        embed.add_field(
            name="Status",
            value="Online",
            inline=True
        )

        embed.add_field(
            name="Changes",
            value=notes_text,
            inline=False
        )

        embed.set_footer(
            text="Auralis • Update Log"
        )

        await update_channel.send(
            content=build_update_log_mentions(guild),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )


# ─────────────────────────────────────────────
# Message Listener
# ─────────────────────────────────────────────

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild is None:
        return

    handled_update = await handle_clean_update_message(message)

    if handled_update:
        return

    await handle_demo_upload_message(message)


# ─────────────────────────────────────────────
# Clean Collaboration Update System
# ─────────────────────────────────────────────

async def handle_clean_update_message(message: discord.Message):
    match = re.match(
        r"^\s*n[\s:,-]+(.+)$",
        message.content,
        re.IGNORECASE
    )

    if not match:
        return False

    update_text = match.group(1).strip()

    if not update_text:
        return False

    update_channel = await get_or_create_update_channel(
        message.guild
    )

    try:
    await message.channel.send(
        f"📝 **{message.author.display_name}**\n\n{update_text}"
    )
except Exception as error:
    print(
        f"Failed to repost clean update message: {error}"
    )

    mention_text = build_mentions(
        message.guild,
        message.author
    )

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

    await update_channel.send(
        content=mention_text,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            everyone=False,
            users=True,
            roles=False
        )
    )

    return True


# ─────────────────────────────────────────────
# Automatic Demo Upload System
# ─────────────────────────────────────────────

async def handle_demo_upload_message(message: discord.Message):
    if "song-demos" not in message.channel.name:
        return

    if not message.attachments:
        return

    audio_files = [
        attachment for attachment in message.attachments
        if is_audio_file(attachment.filename)
    ]

    if not audio_files:
        return

    update_channel = await get_or_create_update_channel(
        message.guild
    )

    mention_text = build_mentions(
        message.guild,
        message.author
    )

    now = discord.utils.utcnow()

    song_name = get_song_name_from_channel(
        message.channel.name
    )

    note_text = message.content.strip()

    if not note_text:
        note_text = "No notes provided."

    file_text = "\n".join(
        [f"• {attachment.filename}" for attachment in audio_files]
    )

    embed = discord.Embed(
        title="🎧 New Demo Uploaded",
        color=0x00FF7F
    )

    embed.add_field(
        name="Song",
        value=song_name,
        inline=True
    )

    embed.add_field(
        name="Channel",
        value=message.channel.mention,
        inline=True
    )

    embed.add_field(
        name="Uploaded By",
        value=message.author.mention,
        inline=True
    )

    embed.add_field(
        name="File",
        value=file_text,
        inline=False
    )

    embed.add_field(
        name="Notes",
        value=note_text,
        inline=False
    )

    embed.add_field(
        name="Time",
        value=discord.utils.format_dt(now, style="F"),
        inline=False
    )

    embed.add_field(
        name="Original Upload",
        value=f"[Open Original Upload]({message.jump_url})",
        inline=False
    )

    embed.set_footer(
        text="Auralis • Demo Upload Log"
    )

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

        demo_channel_name = f"{clean_name}-song-demos"

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
        description="Organization and collaboration tools for songwriting.",
        color=0x00FF7F
    )

    embed.add_field(
        name="/newsong",
        value="Create a full song project.",
        inline=False
    )

    embed.add_field(
        name="/add_demos_channels",
        value="Add missing song-demos channels to old projects.",
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
        name="n / N your message",
        value=(
            "Type `n your update`, `N your updat
