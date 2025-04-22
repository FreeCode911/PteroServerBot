# PteroServerBot

A Discord bot for managing Pterodactyl Panel servers. This bot allows users to link their Discord accounts to the Pterodactyl Panel and create game servers with predefined resource configurations.

## Features

- `/link` command: Authenticates users and links their Discord account to the Pterodactyl Panel
- `/create` command: Creates a new server based on predefined templates
- `/delete` command: Delete one of your servers
- `/reset-password` command: Reset your Pterodactyl panel password
- `/panel-info` command: Get information about the Pterodactyl panel configuration
- `/servers` command: Lists all servers owned by the user
- `/templates` command: Lists all available server templates with their specifications
- User limit: Each user can create up to 2 servers
- Automatic allocation creation: The bot automatically finds available nodes and allocations

## Prerequisites

- Python 3.8 or higher
- A Discord bot token
- A Pterodactyl Panel with API access

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/FreeCode911/PteroServerBot.git
   cd PteroServerBot
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example` and fill in your credentials:
   ```
   cp .env.example .env
   # Edit the .env file with your favorite text editor
   ```

4. Configure your server templates in `config.py` according to your needs.

## Setting up the Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" tab and create a bot
4. Enable the "Message Content Intent" under Privileged Gateway Intents
5. Copy the bot token and add it to your `.env` file
6. Go to the "OAuth2" tab
7. Under "URL Generator", select the following scopes:
   - `bot`
   - `applications.commands`
8. Under "Bot Permissions", select:
   - "Send Messages"
   - "Embed Links"
   - "Use Slash Commands"
9. Copy the generated URL and use it to invite the bot to your server

## Setting up Pterodactyl API

1. Log in to your Pterodactyl Panel as an administrator
2. Go to "Application API" in the admin area
3. Create a new API key with the following permissions:
   - Users: Read & Write
   - Servers: Read & Write
   - Allocations: Read
   - Locations: Read
   - Nests: Read
4. Copy the API key and add it to your `.env` file

## Usage

1. Start the bot:
   ```
   python main.py
   ```

2. In Discord, use the following commands:
   - `/link` - Link your Discord account to Pterodactyl
   - `/templates` - View available server templates
   - `/create <template>` - Create a new server with the specified template
   - `/servers` - List all your servers

## Customizing Server Templates

You can customize the server templates in the `config.py` file. Each template defines the resources allocated to the server, such as RAM, CPU, and disk space.

Example:
```python
SERVER_TEMPLATES = {
    'softerwire': {
        'name': 'Softerwire',
        'description': 'Softerwire Server',
        'memory': 4096,  # RAM in MB
        'disk': 2048,    # Disk space in MB
        'cpu': 200,      # CPU limit (300 = 3 cores)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 25,       # Egg ID (default is 1 for Vanilla Minecraft)
    },
    # Add more templates as needed
}
```
