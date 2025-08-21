import requests
import json
import time
import discord
from discord.ext import commands
from datetime import datetime
import pytz
import asyncio
import os
import aiohttp
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BEARISH_API = "https://www.bearish.af/api/metadata/bearish/{}"
RESERVOIR_API_BASE = "https://api-abstract.reservoir.tools/tokens/v7"
RESERVOIR_API_KEY = os.getenv("RESERVOIR_API_KEY")
BEARISH_CONTRACT_ADDRESS = "0x516dc288e26b34557f68ea1c1ff13576eff8a168"
JSON_FILE = "unrevealed_bearish_tokens.json"
CHECK_INTERVAL = 360  # 6 minutes
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
BEARISH_LOGO = "https://www.bearish.af/_next/image?url=%2Fimages%2FLogo-Bearish-3D.png&w=640&q=75&dpl=dpl_GJqzJhgqjcyBZs5xdKYRuuCXZZdp"

# Local image paths - Create these folders and save your GIFs here
IMAGES_FOLDER = "images"
ICE_IMAGE = "images/ice2.png"
CRACK_IMAGE = "images/crack2.png"
CRACK3_IMAGE = "images/crack3.png"
CRACK_LIGHT_IMAGE = "images/cracklight.png"
BEARISH_LOGO_LOCAL = "images/bearish.png"

# Rarity color mapping
RARITY_COLORS = {
    "Common": 0x808080,
    "Uncommon": 0x00FF00,
    "Rare": 0x0000FF,
    "Epic": 0x800080,
    "Legendary": 0xFFD700
}

# Custom Emojis
SPIN_EMOJI = "<a:spinner:1352643463199588394>"
EXCITED_EMOJI = "<a:bearishaf:1352643338893004861>"
BROWN_BEAR = ":bear:"
GUN_EMOJI = "<a:zgun:1352643509110177874>"
ACTUALLY_BEARISH = "<a:bearishaf:1352643338893004861>"
BERRY_SCROLL = "<:berry:1352643151118205050>"
CLAP_EMOJI = "<:berry:1352643151118205050>"
FIRE_EMOJI = "<a:izfireeee:1352644821201846362>"
GREEN_BEAR = "<:greenb:1352645831446237254>"
MAGIC_EMOJI = "<a:magic:1352643612231471106>" 
EYE_EMOJI = "<:greenb:1352645831446237254>"
# Set up Discord bot
intents = discord.Intents.default()
intents.messages = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_bearish_metadata(token_id):
    """Fetch metadata using Bearish API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BEARISH_API.format(token_id)) as response:
                response.raise_for_status()
                return await response.json()
    except Exception as e:
        print(f"Error fetching Bearish metadata for ID {token_id}: {e}")
        return None

async def get_reservoir_metadata(token_id):
    """Fetch metadata using Reservoir API for rarity (on-demand)."""
    headers = {"x-api-key": RESERVOIR_API_KEY}
    params = {
        "tokens": f"{BEARISH_CONTRACT_ADDRESS}:{token_id}",
        "includeAttributes": "true"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RESERVOIR_API_BASE, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                if "tokens" in data and len(data["tokens"]) > 0:
                    return data["tokens"][0]["token"]
                return None
    except Exception as e:
        print(f"Error fetching Reservoir metadata for ID {token_id}: {e}")
        return None

def get_rarity(metadata):
    """Determine rarity using Reservoir's rarityRank (for !rarity command)."""
    if not metadata:
        return "Common", "N/A"
    rank = metadata.get('rarityRank', "N/A")
    if isinstance(rank, (int, float)):
        if rank <= 100:
            return "Legendary", rank
        elif rank <= 500:
            return "Epic", rank
        elif rank <= 1500:
            return "Rare", rank
        elif rank <= 2500:
            return "Uncommon", rank
        return "Common", rank
    return "Common", "N/A"

def get_price_info(metadata):
    """Get price info from Reservoir metadata (for !rarity command)."""
    if not metadata or 'collection' not in metadata:
        return "Not available"
    
    floor_price = metadata['collection'].get('floorAskPrice', {}).get('amount', {})
    floor_eth = floor_price.get('decimal', 0)
    floor_usd = floor_price.get('usd', 0)
    
    rarest_attr = min(metadata.get('attributes', []), key=lambda x: x['tokenCount'], default={})
    rare_attr_floor = rarest_attr.get('floorAskPrice', {}).get('amount', {}).get('decimal', 0)
    
    return (f"{MONEY_EMOJI} **Floor Price**: {floor_eth:.3f} ETH (${floor_usd:.2f})\n"
            f"{GUN_EMOJI} **Rarest Trait** ({rarest_attr.get('key', 'N/A')}): {rare_attr_floor:.3f} ETH")

def is_unrevealed(metadata):
    """Check if the token is unrevealed using Bearish API data."""
    if not metadata:
        return False
    return "isRevealed" in metadata and not metadata["isRevealed"]

def format_revealed_at(revealed_at):
    """Format revealedAt date to human-readable UTC (e.g., 2025-03-21 02:47 UTC)."""
    if not revealed_at:
        return "N/A"
    try:
        dt = datetime.strptime(revealed_at, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=pytz.UTC)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return "N/A"
    
async def send_status_embed(channel, unrevealed_count):
    """Send an initial status embed with Bearish logo."""
    embed = discord.Embed(
        title="BEARISH NFT Reveal Bot",
        description=f"Monitoring **{unrevealed_count}** unrevealed NFTs",
        color=0x00FFFF
    )
    embed.set_thumbnail(url=BEARISH_LOGO)
    embed.add_field(
        name="Bear Den",
        value="[BEARISH.AF](https://bearish.af)\n[Twitter](https://twitter.com/bearish_af)",
        inline=False
    )
    embed.set_footer(text="Bearish AF", icon_url=BEARISH_LOGO)
    await channel.send(embed=embed)

async def create_reveal_gif(token_id, final_nft_url):
    """Create a GIF with the reveal sequence: ice1.png → crack2.png → light.png → final NFT."""
    try:
        # Load the local images
        images = []
        durations = []
        
        # Add ice cube image (1 second)
        if os.path.exists(ICE_IMAGE):
            images.append(Image.open(ICE_IMAGE))
            durations.append(1000)
        
        # Add crack2 image (1 second)
        if os.path.exists(CRACK_IMAGE):
            images.append(Image.open(CRACK_IMAGE))
            durations.append(1000)
        
        # Add crack3 image (1 second)
        if os.path.exists(CRACK3_IMAGE):
            images.append(Image.open(CRACK3_IMAGE))
            durations.append(1000)
        
        # Download and add final NFT image (5 seconds - longer than all others combined)
        if final_nft_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(final_nft_url, timeout=10) as response:
                        if response.status == 200:
                            nft_data = await response.read()
                            nft_image = Image.open(io.BytesIO(nft_data))
                            images.append(nft_image)
                            durations.append(5000)  # 5 seconds for final image
                        else:
                            print(f"Failed to download NFT image for token #{token_id}: HTTP {response.status}")
            except Exception as e:
                print(f"Error downloading NFT image for token #{token_id}: {e}")
                # Continue without the NFT image if download fails
        
        if len(images) < 2:
            print(f"Not enough images to create GIF for token #{token_id}")
            return None
        
        # Resize all images to the same size (use the first image as reference)
        base_size = images[0].size
        resized_images = []
        for img in images:
            resized_img = img.resize(base_size, Image.Resampling.LANCZOS)
            resized_images.append(resized_img)
        
        # Create GIF with custom durations
        gif_buffer = io.BytesIO()
        resized_images[0].save(
            gif_buffer,
            format='GIF',
            save_all=True,
            append_images=resized_images[1:],
            duration=durations,
            loop=0  # Loop once
        )
        gif_buffer.seek(0)
        
        return gif_buffer
        
    except Exception as e:
        print(f"Error creating GIF for token #{token_id}: {e}")
        return None

async def send_reveal_sequence(channel, token_id, metadata):
    """Send a single reveal GIF with the entire animation sequence."""
    
    # Create a single embed for the reveal
    embed = discord.Embed(
        title=f"Bearish NFT #{token_id} Revealed!",
        description="🧊🧊🧊🧊🧊🧊",
        color=0x00BFFF  # Deep sky blue for final reveal
    )
    
    # Add attributes WITHOUT "Traits" label
    attributes = metadata.get('attributes', [])
    print(f"Token #{token_id} has {len(attributes)} attributes")
    if attributes:
        print(f"Attributes: {attributes}")
        # Use Discord's small text formatting (tiny writing with -#)
        attr_str = "\n".join([f"-# {attr['trait_type']}: {attr['value']}" for attr in attributes])
        print(f"Traits string: {attr_str}")
        # Split into multiple fields if too long
        if len(attr_str) > 1024:
            # Split into chunks
            chunks = [attr_str[i:i+1024] for i in range(0, len(attr_str), 1024)]
            for i, chunk in enumerate(chunks):
                embed.add_field(name="", value=chunk, inline=False)
        else:
            embed.add_field(name="", value=attr_str, inline=False)
    else:
        print(f"No attributes found for token #{token_id}")
    
    # Add marketplace links on one line
    magic_eden_link = f"https://magiceden.io/item-details/abstract/bearish/{token_id}"
    opensea_link = f"https://opensea.io/assets/ethereum/{BEARISH_CONTRACT_ADDRESS}/{token_id}"
    embed.add_field(name="", value=f"[Magic Eden]({magic_eden_link}) | [OpenSea]({opensea_link})", inline=False)
    
    # Create the reveal GIF
    final_nft_image = metadata.get('image')
    
    try:
        gif_buffer = await create_reveal_gif(token_id, final_nft_image)
        
        if gif_buffer:
            # Send the GIF file
            gif_file = discord.File(gif_buffer, filename=f"reveal_{token_id}.gif")
            embed.set_image(url=f"attachment://reveal_{token_id}.gif")
            await channel.send(embed=embed, file=gif_file)
        else:
            # Fallback to just the final NFT image
            if final_nft_image:
                embed.set_image(url=final_nft_image)
            else:
                embed.set_thumbnail(url=BEARISH_LOGO)
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending reveal for token #{token_id}: {e}")
        # Fallback: send without GIF
        if final_nft_image:
            embed.set_image(url=final_nft_image)
        else:
            embed.set_thumbnail(url=BEARISH_LOGO)
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    """Bot startup event: Start monitoring unrevealed tokens."""
    print(f"Bot logged in as {bot.user}!")
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        print(f"Error: Channel ID {DISCORD_CHANNEL_ID} not found.")
        return

    while True:
        try:
            with open(JSON_FILE, "r") as f:
                unrevealed = json.load(f)
            print(f"Loaded {len(unrevealed)} unrevealed tokens from {JSON_FILE}.")
            break
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            print(f"Error reading {JSON_FILE}. Retrying in 10 seconds...")
            await asyncio.sleep(10)

    if not unrevealed:
        print("No unrevealed tokens to monitor.")
        return

    await send_status_embed(channel, len(unrevealed))
    print("Bot locked and loaded! Monitoring started.")

    while unrevealed:
        print(f"Sniffing out {len(unrevealed)} unrevealed tokens...")
        updated_unrevealed = []
        for token_id in unrevealed[:]:
            print(f"Checking token #{token_id}...")
            bearish_metadata = await get_bearish_metadata(token_id)
            
            if bearish_metadata:
                print(f"Token #{token_id} metadata: {bearish_metadata.get('isRevealed', 'N/A')}")
                if not is_unrevealed(bearish_metadata):
                    print(f"Token #{token_id} revealed! {GUN_EMOJI} Fetching the goods...")
                    await send_reveal_sequence(channel, token_id, bearish_metadata)
                    print(f"Token #{token_id} blasted out and removed from the den!")
                else:
                    print(f"Token #{token_id} still unrevealed")
                    updated_unrevealed.append(token_id)
            else:
                print(f"Token #{token_id} - No metadata received, keeping in list")
                updated_unrevealed.append(token_id)
        
        unrevealed = updated_unrevealed
        with open(JSON_FILE, "w") as f:
            json.dump(unrevealed, f)
            print(f"Updated {JSON_FILE} with {len(unrevealed)} bears still hiding.")
        
        if not unrevealed:
            print(f"All bears revealed! Party time! {CLAP_EMOJI}")
            break
        
        print(f"Hibernating for {CHECK_INTERVAL // 60} minutes... {BROWN_BEAR}")
        await asyncio.sleep(CHECK_INTERVAL)

@bot.command()
async def rarity(ctx, token_id: int):
    """Command: !rarity ID - Fetch rarity from Reservoir API."""
    if ctx.channel.id != DISCORD_CHANNEL_ID:
        return  # Only respond in the specified channel

    # Fetch metadata from Reservoir
    metadata = await get_reservoir_metadata(token_id)
    if not metadata:
        await ctx.send(f"Couldn't fetch data for Bearish NFT #{token_id}. Try again later! 🐻")
        return

    rarity, rank = get_rarity(metadata)
    embed = discord.Embed(
        title=f"{SPIN_EMOJI} Bearish NFT #{token_id} Rarity Check {ACTUALLY_BEARISH}",
        description=f"{EXCITED_EMOJI} Let's see how rare this bear is! {FIRE_EMOJI}\n**Rarity**: {rarity} (Rank: {rank}) {CLAP_EMOJI}",
        color=RARITY_COLORS.get(rarity, 0x808080)
    )

    # Image
    image_url = metadata.get('image')
    if image_url:
        embed.set_image(url=image_url)
    else:
        embed.set_thumbnail(url=BEARISH_LOGO)

    # Attributes
    attributes = metadata.get('attributes', [])
    if attributes:
        attr_str = "\n".join([f"{BERRY_SCROLL} {attr['key']}: **{attr['value']}** (Rarity: {attr['tokenCount']})" 
                            for attr in attributes])
        embed.add_field(name=f"{EYE_EMOJI} Bearish Traits", value=attr_str[:1024], inline=False)

    # Price Info
    price_info = get_price_info(metadata)
    embed.add_field(name=f"{MONEY_EMOJI} Market Heat", value=price_info, inline=False)

    # Marketplace Links
    reservoir_link = f"https://reservoir.market/abstract/collections/bearish/{token_id}"
    magic_eden_link = f"https://magiceden.io/item-details/abstract/bearish/{token_id}"
    embed.add_field(
        name=f"{BROWN_BEAR} Hunt It Down",
        value=f"{BERRY_SCROLL} [Reservoir]({reservoir_link})\n{BERRY_SCROLL} [Magic Eden]({magic_eden_link})",
        inline=False
    )

    embed.set_footer(text="Bearish AF", icon_url=BEARISH_LOGO)
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx, token_id: int):
    """Command: !test ID - Test if a specific token is revealed."""
    if ctx.channel.id != DISCORD_CHANNEL_ID:
        return  # Only respond in the specified channel

    await ctx.send(f"Testing token #{token_id}...")
    
    # Fetch metadata
    metadata = await get_bearish_metadata(token_id)
    if not metadata:
        await ctx.send(f"❌ Could not fetch metadata for token #{token_id}")
        return
    
    # Check reveal status
    is_revealed = not is_unrevealed(metadata)
    revealed_at = format_revealed_at(metadata.get("revealedAt"))
    
    status_msg = f"**Token #{token_id} Status:**\n"
    status_msg += f"• **Revealed:** {'✅ Yes' if is_revealed else '❌ No'}\n"
    status_msg += f"• **Revealed At:** {revealed_at}\n"
    status_msg += f"• **isRevealed field:** {metadata.get('isRevealed', 'N/A')}\n"
    
    if is_revealed:
        status_msg += f"• **Image:** {metadata.get('image', 'N/A')}\n"
        status_msg += f"• **Attributes:** {len(metadata.get('attributes', []))} traits\n"
    
    await ctx.send(status_msg)

if __name__ == "__main__":

    bot.run(DISCORD_BOT_TOKEN) 
