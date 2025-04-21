import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')

# Pterodactyl Panel Configuration
PTERODACTYL_URL = os.getenv('PTERODACTYL_URL')
PTERODACTYL_API_KEY = os.getenv('PTERODACTYL_API_KEY')

# Web Server Configuration
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
WEB_HOST = os.getenv('WEB_HOST', 'localhost')
WEB_PORT = int(os.getenv('WEB_PORT', 5000))

# Server Templates Configuration
SERVER_TEMPLATES = {
    'nodejs': {
        'name': 'NodeJS',
        'description': 'NodeJS server',
        'memory': 4096,  # RAM in MB
        'disk': 2048,   # Disk space in MB
        'cpu': 200,      # CPU limit (100 = 1 core)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 16,        # Egg ID (default is 1 for Vanilla Minecraft)
    },
    'python': {
        'name': 'Python',
        'description': 'Python server',
        'memory': 4096,  # RAM in MB
        'disk': 2048,   # Disk space in MB
        'cpu': 200,      # CPU limit (100 = 1 core)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 15,        # Egg ID (default is 1 for Vanilla Minecraft)
    },
    'lavalink': {
        'name': 'Lavalink',
        'description': 'Lavalink server',
        'memory': 1024,  # RAM in MB
        'disk': 500,   # Disk space in MB
        'cpu': 200,      # CPU limit (300 = 3 cores)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 17,        # Egg ID (default is 1 for Vanilla Minecraft)
    },
    'uptimekuma': {
        'name': 'UptimeKuma',
        'description': 'UptimeKuma server',
        'memory': 1024,  # RAM in MB
        'disk': 500,   # Disk space in MB
        'cpu': 200,      # CPU limit (300 = 3 cores)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 22,        # Egg ID (default is 1 for Vanilla Minecraft)
    # Add more templates as needed
    },
    'web-hosting': {
        'name': 'Web Hosting',
        'description': 'Web hosting server',
        'memory': 3072,  # RAM in MB
        'disk': 2048,   # Disk space in MB
        'cpu': 200,      # CPU limit (300 = 3 cores)
        'nest': 5,       # Nest ID (default is 1 for Minecraft)
        'egg': 24,        # Egg ID (default is 1 for Vanilla Minecraft)
        'env': {
            'PHP_VERSION': '8.4'
        }
    }
}

# User Limits
MAX_SERVERS_PER_USER = 2

# Database for tracking user servers (simple in-memory for now)
# In a production environment, you would use a real database
USER_SERVERS = {}  # Format: {discord_user_id: [server_id1, server_id2, ...]}
USER_AUTH_CODES = {}  # Format: {auth_code: discord_user_id}
PTERODACTYL_USERS = {}  # Format: {discord_user_id: pterodactyl_user_id}
