import os
from bot import main as bot_main
from dotenv import load_dotenv
from config import DISCORD_BOT_TOKEN, PTERODACTYL_URL, PTERODACTYL_API_KEY

def check_environment():
    """Check if all required environment variables are set"""
    missing_vars = []

    if not DISCORD_BOT_TOKEN:
        missing_vars.append("DISCORD_BOT_TOKEN")

    if not PTERODACTYL_URL:
        missing_vars.append("PTERODACTYL_URL")

    if not PTERODACTYL_API_KEY:
        missing_vars.append("PTERODACTYL_API_KEY")

    if missing_vars:
        print("Error: The following environment variables are missing:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease create a .env file based on .env.example and fill in the required values.")
        return False

    return True

def main():
    """Main entry point for the application"""
    # Load environment variables
    load_dotenv()

    # Print environment variables for debugging
    print(f"DISCORD_BOT_TOKEN: {'*' * 10}{DISCORD_BOT_TOKEN[-5:] if DISCORD_BOT_TOKEN else 'None'}")
    print(f"PTERODACTYL_URL: {PTERODACTYL_URL if PTERODACTYL_URL else 'None'}")
    print(f"PTERODACTYL_API_KEY: {'*' * 10}{PTERODACTYL_API_KEY[-5:] if PTERODACTYL_API_KEY else 'None'}")

    # Check if all required environment variables are set
    if not check_environment():
        return

    print("Starting bot...")
    # Start the bot
    try:
        bot_main()
    except Exception as e:
        print(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()
