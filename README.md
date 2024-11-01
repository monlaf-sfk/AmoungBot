# Real-Life Among Us Telegram Bot 🎮

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![License](https://img.shields.io/badge/license-MIT-blue)

## About
A real-life adaptation of *Among Us* that uses a Telegram bot to manage gameplay. Players join a live game, find assigned targets in person, and "eliminate" them by collecting unique codes. The last player standing is declared the winner.

## Features
- ✅ Real-time target assignment and reassignment upon eliminations
- ✅ Automated tracking of player stats, kills, and inactivity
- ✅ Top-player rankings and progress tracking during gameplay
- ✅ Direct support communication with game administrators

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Commands](#commands)
- [Contributing](#contributing)
- [License](#license)

## Installation

```bash
# Clone the repository
git clone https://github.com/username/real-life-among-us-bot.git
cd real-life-among-us-bot

# Install dependencies
pip install -r requirements.txt
```

## Usage
```bash
# Start the bot
python bot.py
```
1. **Invite Players**: Players register through the bot using the `/register` command. The admin then starts the game.
2. **Gameplay**: Players find their targets in real life and submit their codes to "eliminate" them.
3. **Game End**: The game ends when one player remains, and final rankings are announced.

## Configuration

Create a `.env` file with the following variables:

```plaintext
TELEGRAM_API_TOKEN=<your-telegram-bot-token>
DATABASE_URL=<your-database-url>
CHANNEL_ID=<your-channel-id-for-notifications>
```

## Commands
- `/register`: Join the game
- `/start_game`: Start the game (admin-only)
- `/status`: View your current game status and target
- `/support`: Contact game admin for assistance
- `/current_game`: Get live stats and progress of the game

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository
2. Create a new branch (`feature/your-feature`)
3. Commit your changes
4. Open a pull request

## License
This project is licensed under the MIT License.

--- 

This concise README covers all key aspects, making it easy for users to set up and understand the bot's core functions and commands.
