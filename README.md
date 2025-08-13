# Bearish NFT Reveal Bot

A Discord bot that monitors unrevealed Bearish NFTs and sends animated reveal notifications when they become available.

## Features

- 🧊 **Animated Reveal Sequence**: Ice cube → Crack → Final NFT with custom timing
- 📊 **Real-time Monitoring**: Checks unrevealed tokens every 6 minutes
- 🎨 **Clean Design**: Minimal embed with traits and marketplace links
- 🔗 **Marketplace Integration**: Direct links to Magic Eden and OpenSea

## Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd bearish-reveal-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
DISCORD_GUILD_ID=your_guild_id_here
RESERVOIR_API_KEY=your_reservoir_api_key_here
```

### 4. Add Images
Place the following images in the `images/` folder:
- `ice1.png` - Ice cube image
- `crack2.png` - First crack image
- `crack3.png` - Second crack image
- `cracklight.png` - Light effect image (optional)

### 5. Configure Token List
Create `unrevealed_bearish_tokens.json` with an array of token IDs:
```json
[1, 2, 3, 4, 5, ...]
```

### 6. Run the Bot
```bash
python floor1.py
```

## Usage

### Commands
- `!rarity <token_id>` - Check rarity of a specific token
- `!test <token_id>` - Test if a token is revealed

### Reveal Sequence
When a token is revealed, the bot sends:
1. **Animated GIF**: ice1.png → crack2.png → crack3.png → final NFT (5s)
2. **Traits**: Small text format with `-#` prefix
3. **Marketplace Links**: Magic Eden and OpenSea

## Configuration

### Timing
- **Check Interval**: 6 minutes (360 seconds)
- **GIF Frame Duration**: 1 second each for animation, 5 seconds for final NFT
- **API Endpoints**: Bearish API and Reservoir API

### Customization
- Modify `CHECK_INTERVAL` for different monitoring frequency
- Adjust GIF durations in `create_reveal_gif()` function
- Update marketplace links in `send_reveal_sequence()`

## Requirements

- Python 3.8+
- Discord Bot Token
- Reservoir API Key
- Bearish NFT collection access

## License

This project is for Bearish NFT community use. 
