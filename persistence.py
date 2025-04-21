import json
import os
import threading

# File paths for data storage
DATA_DIR = "data"
USER_SERVERS_FILE = os.path.join(DATA_DIR, "user_servers.json")
USER_AUTH_CODES_FILE = os.path.join(DATA_DIR, "user_auth_codes.json")
PTERODACTYL_USERS_FILE = os.path.join(DATA_DIR, "pterodactyl_users.json")

# Lock for thread-safe file operations
file_lock = threading.Lock()

def ensure_data_dir():
    """Ensure the data directory exists"""
    os.makedirs(DATA_DIR, exist_ok=True)

def load_data(file_path, default=None):
    """Load data from a JSON file"""
    if default is None:
        default = {}
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return default
    except Exception as e:
        print(f"Error loading data from {file_path}: {e}")
        return default

def save_data(file_path, data):
    """Save data to a JSON file"""
    with file_lock:
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving data to {file_path}: {e}")
            return False

def load_user_servers():
    """Load user servers data"""
    ensure_data_dir()
    data = load_data(USER_SERVERS_FILE)
    # Convert keys back to strings (JSON converts them to strings during serialization)
    return {str(k): v for k, v in data.items()}

def save_user_servers(user_servers):
    """Save user servers data"""
    ensure_data_dir()
    return save_data(USER_SERVERS_FILE, user_servers)

def load_user_auth_codes():
    """Load user auth codes data"""
    ensure_data_dir()
    data = load_data(USER_AUTH_CODES_FILE)
    return {str(k): v for k, v in data.items()}

def save_user_auth_codes(user_auth_codes):
    """Save user auth codes data"""
    ensure_data_dir()
    return save_data(USER_AUTH_CODES_FILE, user_auth_codes)

def load_pterodactyl_users():
    """Load pterodactyl users data"""
    ensure_data_dir()
    data = load_data(PTERODACTYL_USERS_FILE)
    return {str(k): v for k, v in data.items()}

def save_pterodactyl_users(pterodactyl_users):
    """Save pterodactyl users data"""
    ensure_data_dir()
    return save_data(PTERODACTYL_USERS_FILE, pterodactyl_users)
