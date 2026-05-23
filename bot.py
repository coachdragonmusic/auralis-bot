Here is your fully updated, consolidated script. I have applied the `max_values=len(options)` dynamic UI fix to `ChannelDeleteSelect` so it won't crash when servers have fewer than 25 channels, and I have scrubbed out all of the weird spacing compression that happened during transmission to restore clean PEP 8 indentation.

```python
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
# Configuration Profiles
# ─────────────────────────────────────────────

UPDATE_CHANNEL_NAME = "song-updates"
COLLAB_CATEGORY_NAME = "📢 Collaboration"
AURALIS_UPDATE_CHANNEL = "auralis-update-log"

BOT_VERSION = "1.3"

BOT_UPDATE_NOTES = [
    "Initial Auralis release framework setup.",
    "Added /newsong for automatic project category deployment.",
    "Added /clean_channels and /clean_categories workspace maintenance suites.",
    "Integrated dynamic text logging utilizing the 'n / N' message prefixes.",
    "Automated tracking pipelines for #song-demos audio submissions.",
    "Implemented dedicated #final-exports tracking optimized for LANDR mastering outputs.",
    "Fixed variable mappings and improved string parsing efficiency."
]

COLLABORATORS = [
    "CoachDragon",
    "mizuki17"
]

UPDATE_NOTIFY_USERS = [
    "mizuki17"
]

AUDIO_EXTENSIONS = (
    ".mp3", 
    ".wav", 
    ".m4a", 
    ".flac", 
    ".ogg"
)

# Multi-guild runtime tracker for safe deployment logging
_logged_guilds = set()

# ─────────────────────────────────────────────
# Discord Client Framework Initialization
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ─────────────────────────────────────────────
# Identity & Collaboration Helper Functions
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
    name = name.replace("-final-exports", "")
    name = name.replace("-", " ")
    return name.title()


def is_audio_file(filename: str) -> bool:
    return filename.lower().endswith(AUDIO_EXTENSIONS)


def is_song_category(category: discord.CategoryChannel) -> bool:
    if category.name.startswith("🎵"):
        return True

    keywords = ["lyrics", "prompts", "revisions", "mixing-notes", "song-demos", "final-exports"]
    matches = 0

    for channel in category.channels:
        for keyword in keywords:
            if keyword in channel.name:
                matches += 1
                break

    return matches >= 2


def find_members_by_names(guild: discord.Guild, names: list[str]) -> list[discord.Member]:
    found_members = []
    for member in guild.members:
        if member.bot:
            continue

        for username in names:
            clean_name = username.lower().replace("@", "")
            matched = False

            if member.name and member.name.lower() == clean_name:
                matched = True
            elif member.display_name and member.display_name.lower() == clean_name:
                matched = True
            elif member.global_name and member.global_name.lower() == clean_name:
                matched = True

            if matched:
                found_members.append(member)
                break
                
    return found_members


def build_collab_mentions(guild: discord.Guild, author: discord.Member) -> str:
    members = find_members_by_names(guild, COLLABORATORS)
    notify_members = [m for m in members if m.id != author.id]
    return " ".join([member.mention for member in notify_members])


def build_update_log_mentions(guild: discord.Guild) -> str:
    notify_members = find_members_by_names(guild, UPDATE_NOTIFY_USERS)
    return " ".join(list(set(member.mention for member in notify_members)))


# ─────────────────────────────────────────────
# Channel Infrastructure Provisioning
# ─────────────────────────────────────────────

async def get_or_create_update_channel(guild: discord.Guild) -> discord.TextChannel:
    channel = discord.utils.get(guild.text_channels, name=UPDATE_CHANNEL_NAME)
    if channel is not None:
        return channel

    category = discord.utils.get(guild.categories, name=COLLAB_CATEGORY_NAME)
    if category is None:
        category = await guild.create_category(COLLAB_CATEGORY_NAME)

    return await guild.create_text_channel(UPDATE_CHANNEL_NAME, category=category)


async def get_or_create_auralis_update_channel(guild: discord.Guild) -> discord.TextChannel:
    channel = discord.utils.get(guild.text_channels, name=AURALIS_UPDATE_CHANNEL)
    if channel is not None:
        return channel

    return await guild.create_text_channel(AURALIS_UPDATE_CHANNEL)


async def version_already_logged(channel: discord.TextChannel, version: str) -> bool:
    async for old_message in channel.history(limit=50):
        if old_message.author != client.user:
            continue

        for embed in old_message.embeds:
            for field in embed.fields:
                if field.name == "Version" and field.value == version:
                    return True
    return False

# ─────────────────────────────────────────────
# Automated Logging Pipeline Actions
# ─────────────────────────────────────────────

async def handle_clean_update_message(message: discord.Message) -> bool:
    match = re.match(r"^\s*([nN])[\s:,-]+(.+)$", message.content)
    if not match:
        return False

    update_text = match.group(2).strip()
    if not update_text:
        return False

    try:
        await message.delete()
    except Exception as error:
        print(f"Failed to delete original update trigger message: {error}")

    update_channel = await get_or_create_update_channel(message.guild)

    try:
        await message.channel.send(f"📝 **{message.author.display_name}**\n\n{update_text}")
    except Exception as error:
        print(f"Failed to repost clean update message: {error}")

    mention_text = build_collab_mentions(message.guild, message.author)
    now = discord.utils.utcnow()

    embed = discord.Embed(title="🔔 New Song Update", description=update_text, color=0x00FF7F)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Updated By", value=message.author.mention, inline=True)
    embed.add_field(name="Time", value=discord.utils.format_dt(now, style="F"), inline=False)
    embed.set_footer(text="Auralis • Song Collaboration Log")

    await update_channel.send(
        content=mention_text,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False)
    )
    return True


async def handle_final_export_message(message: discord.Message) -> bool:
    if "final-exports" not in message.channel.name or not message.attachments:
        return False

    final_files = [a for a in message.attachments if is_audio_file(a.filename)]
    if not final_files:
        return False

    update_channel = await get_or_create_update_channel(message.guild)
    mention_text = build_collab_mentions(message.guild, message.author)
    song_name = get_song_name_from_channel(message.channel.name)
    
    file_text = "\n".join([f"📀 **{a.filename}**" for a in final_files])
    note_text = message.content.strip() or "No additional release notes provided."
    now = discord.utils.utcnow()

    embed = discord.Embed(
        title="🎉 Final Master Delivered!",
        color=0xB026FF,  # Distinct purple profile accentuation for mastering outputs
        description=f"A finalized high-res master has been uploaded to the archives for **{song_name}**."
    )
    embed.add_field(name="Song Project", value=song_name, inline=True)
    embed.add_field(name="Archived In", value=message.channel.mention, inline=True)
    embed.add_field(name="Uploaded By", value=message.author.mention, inline=True)
    embed.add_field(name="Master File(s)", value=file_text, inline=False)
    embed.add_field(name="Notes", value=note_text, inline=False)
    embed.add_field(name="Time", value=discord.utils.format_dt(now, style="F"), inline=False)
    embed.add_field(name="Listen / Download", value=f"[Jump to Master File]({message.jump_url})", inline=False)
    embed.set_footer(text="Auralis • Release Pipeline")

    await update_channel.send(
        content=mention_text,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False)
    )
    return True


async def handle_demo_upload_message(message: discord.Message) -> bool:
    if "song-demos" not in message.channel.name or not message.attachments:
        return False

    audio_files = [a for a in message.attachments if is_audio_file(a.filename)]
    if not audio_files:
        return False

    update_channel = await get_or_create_update_channel(message.guild)
    mention_text = build_collab_mentions(message.guild, message.author)
    song_name = get_song_name_from_channel(message.channel.name)
    
    file_text = "\n".join([f"• {a.filename}" for a in audio_files])
    note_text = message.content.strip() or "No notes provided."
    now = discord.utils.utcnow()

    embed = discord.Embed(title="🎧 New Demo Uploaded", color=0x00FF7F)
    embed.add_field(name="Song", value=song_name, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Uploaded By", value=message.author.mention, inline=True)
    embed.add_field(name="File(s)", value=file_text, inline=False)
    embed.add_field(name="Notes", value=note_text, inline=False)
    embed.add_field(name="Time", value=discord.utils.format_dt(now, style="F"), inline=False)
    embed.add_field(name="Original Upload", value=f"[Open Original Upload]({message.jump_url})", inline=False)
    embed.set_footer(text="Auralis • Demo Upload Log")

    await update_channel.send(
        content=mention_text,
        embed=embed,
        allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False)
    )
    return True

# ─────────────────────────────────────────────
# Core Application Events
# ─────────────────────────────────────────────

@client.event
async def on_ready():
    await tree.sync()
    print(f"Auralis is online as {client.user}")

    for guild in client.guilds:
        if guild.id in _logged_guilds:
            continue

        update_channel = await get_or_create_auralis_update_channel(guild)
        if await version_already_logged(update_channel, BOT_VERSION):
            _logged_guilds.add(guild.id)
            continue

        notes_text = "\n".join([f"• {note}" for note in BOT_UPDATE_NOTES])
        embed = discord.Embed(
            title="🚀 Auralis Updated",
            description="Auralis is online with the latest stable release.",
            color=0x00FF7F
        )
        embed.add_field(name="Version", value=BOT_VERSION, inline=True)
        embed.add_field(name="Status", value="Online", inline=True)
        embed.add_field(name="Changes", value=notes_text, inline=False)
        embed.set_footer(text="Auralis • Update Log")

        await update_channel.send(
            content=build_update_log_mentions(guild),
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False)
        )
        _logged_guilds.add(guild.id)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    if await handle_clean_update_message(message):
        return

    if await handle_final_export_message(message):
        return

    await handle_demo_upload_message(message)

# ─────────────────────────────────────────────
# Guild Application Slash Commands
# ─────────────────────────────────────────────

@tree.command(name="newsong", description="Create a new organized song project workflow workspace.")
@app_commands.describe(title="Song title")
async def newsong(interaction: discord.Interaction, title: str):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return

    await interaction.response.send_message(f"Creating project for **{title}**...", ephemeral=True)
    clean_name = clean_channel_name(title)
    category = await guild.create_category(f"🎵 {title}")

    channels = [
        f"{clean_name}-lyrics",
        f"{clean_name}-prompts",
        f"{clean_name}-revisions",
        f"{clean_name}-mixing-notes",
        f"{clean_name}-song-demos",
        f"{clean_name}-final-exports"
    ]

    for channel_name in channels:
        await guild.create_text_channel(channel_name, category=category)


@tree.command(name="add_demos_channels", description="Add missing song-demos channels to existing song categories.")
async def add_demos_channels(interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("You need Manage Channels permission to use this.", ephemeral=True)
        return

    await interaction.response.send_message("Scanning song categories...", ephemeral=True)
    added_channels = []

    for category in guild.categories:
        if not is_song_category(category):
            continue

        clean_name = clean_song_category_name(category.name)
        demo_channel_name = f"{clean_name}-song-demos"

        if discord.utils.get(category.channels, name=demo_channel_name) is not None:
            continue

        await guild.create_text_channel(demo_channel_name, category=category)
        added_channels.append(f"{category.name} → #{demo_channel_name}")

    if added_channels:
        added_text = "\n".join([f"• {item}" for item in added_channels])
        embed = discord.Embed(title="Song Demo Channels Added", description=added_text, color=0x00FF7F)
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.followup.send("No missing demo channels found.", ephemeral=True)


# ─────────────────────────────────────────────
# UI Interactive View Components
# ─────────────────────────────────────────────

class CategoryDeleteSelect(discord.ui.Select):
    def __init__(self, categories: list[discord.CategoryChannel]):
        options = [discord.SelectOption(label=cat.name[:100], value=str(cat.id)) for cat in categories[:25]]
        super().__init__(placeholder="Choose a category to delete...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category_id = int(self.values[0])
        category = discord.utils.get(interaction.guild.categories, id=category_id)

        if category is None:
            await interaction.response.send_message("That category no longer exists.", ephemeral=True)
            return

        await interaction.response.send_message(f"Deleting **{category.name}** and nested children...", ephemeral=True)
        for channel in list(category.channels):
            await channel.delete()
        await category.delete()


class CategoryDeleteView(discord.ui.View):
    def __init__(self, categories: list[discord.CategoryChannel]):
        super().__init__(timeout=300)
        self.add_item(CategoryDeleteSelect(categories))


class ChannelDeleteSelect(discord.ui.Select):
    def __init__(self, channels: list[discord.TextChannel]):
        options = [discord.SelectOption(label=ch.name[:100], value=str(ch.id)) for ch in channels[:25]]
        super().__init__(
            placeholder="Choose channels to delete...",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Deleting selected target channels...", ephemeral=True)
        for value in self.values:
            channel = discord.utils.get(interaction.guild.text_channels, id=int(value))
            if channel is not None:
                try:
                    await channel.delete()
                except Exception as error:
                    print(f"Error purging channel: {error}")


class ChannelDeleteView(discord.ui.View):
    def __init__(self, channels: list[discord.TextChannel]):
        super().__init__(timeout=300)
        self.add_item(ChannelDeleteSelect(channels))


# ─────────────────────────────────────────────
# Management Channel Operations
# ─────────────────────────────────────────────

@tree.command(name="clean_categories", description="Delete an entire category and all linked channel workflows.")
async def clean_categories(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return

    categories = interaction.guild.categories
    if not categories:
        await interaction.response.send_message("No workspace categories detected.", ephemeral=True)
        return

    await interaction.response.send_message("Pick the category to purge:", view=CategoryDeleteView(categories), ephemeral=True)


@tree.command(name="clean_channels", description="Delete multiple text channel spaces simultaneously.")
async def clean_channels(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return

    channels = interaction.guild.text_channels
    if not channels:
        await interaction.response.send_message("No text environments detected.", ephemeral=True)
        return

    await interaction.response.send_message("Pick targeted channels to drop:", view=ChannelDeleteView(channels), ephemeral=True)


@tree.command(name="help", description="Show the active Auralis project control listing.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Auralis Systems Command Menu",
        description="Core workflow and collaborative deployment tools for studio tracks.",
        color=0x00FF7F
    )
    embed.add_field(name="/newsong", value="Configures full isolated tracking directories for a new song.", inline=False)
    embed.add_field(name="/add_demos_channels", value="Patches legacy tracking directories with missing demo pipelines.", inline=False)
    embed.add_field(name="/clean_channels", value="Pitches targeted tracking instances inside your environment.", inline=False)
    embed.add_field(name="/clean_categories", value="Drops holistic asset structural brackets safely.", inline=False)
    embed.add_field(name="n / N [Message Text]", value="Quickly locks an update note and shares it inside workspace logs.", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─────────────────────────────────────────────
# Execution Launch Hook
# ─────────────────────────────────────────────

client.run(TOKEN)

```
