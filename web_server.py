from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import os
import uuid
import threading
import secrets
import requests
from requests_oauthlib import OAuth2Session
from config import (FLASK_SECRET_KEY, WEB_HOST, WEB_PORT, USER_AUTH_CODES,
                   DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI,
                   PTERODACTYL_USERS)
import persistence

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create a simple HTML template for displaying the auth code
with open('templates/auth_code.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Authentication</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            text-align: center;
        }
        .code-box {
            font-size: 24px;
            font-weight: bold;
            padding: 15px;
            margin: 20px 0;
            background-color: #f0f0f0;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .instructions {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>Discord Bot Authentication</h1>
    <div class="instructions">
        <p>Your authentication code is:</p>
    </div>
    <div class="code-box">
        {{ auth_code }}
    </div>
    <div class="instructions">
        <p>Please copy this code and paste it in Discord where prompted.</p>
        <p>This code will expire in 10 minutes.</p>
    </div>
</body>
</html>
    """)

# Discord OAuth2 Configuration
DISCORD_API_BASE_URL = 'https://discord.com/api'
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

# Discord server membership is no longer required
# The following lines are kept as comments for reference
# REQUIRED_SERVER_ID = '1186648150027554937'
# DISCORD_SERVER_INVITE = 'https://discord.gg/JzDArmmmy7'

# Allow OAuth2 to work with HTTP (for development only)
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Store pterodactyl API instance
pterodactyl_api = None

# Set the pterodactyl API instance
def set_pterodactyl_api(api_instance):
    global pterodactyl_api
    pterodactyl_api = api_instance

@app.route('/')
def index():
    return "Pterodactyl Discord Bot Authentication Server"

@app.route('/auth/<discord_id>')
def auth(discord_id):
    # Generate a unique authentication code
    auth_code = secrets.token_hex(3).upper()  # 6 character hex code

    # Store the auth code with the Discord ID
    USER_AUTH_CODES[auth_code] = discord_id

    # Save the updated auth codes to disk
    persistence.save_user_auth_codes(USER_AUTH_CODES)
    print(f"Saved auth code for Discord user {discord_id}")

    # Set a session variable to track this auth code
    session['auth_code'] = auth_code
    session['discord_id'] = discord_id

    return render_template('auth_code.html', auth_code=auth_code)

@app.route('/oauth')
def oauth():
    """Redirect to Discord OAuth"""
    if 'discord_id' not in session:
        # If no discord_id in session, check if it's in the query parameters
        discord_id = request.args.get('discord_id')
        if discord_id:
            session['discord_id'] = discord_id
        else:
            return render_template('error.html', error="No Discord ID provided. Please use the link from Discord.")

    discord_id = session['discord_id']
    print(f"Starting OAuth flow for Discord ID: {discord_id}")

    # Create OAuth2 session with guilds scope to check server membership
    oauth = OAuth2Session(DISCORD_CLIENT_ID, redirect_uri=DISCORD_REDIRECT_URI, scope=['identify', 'email', 'guilds'])
    authorization_url, state = oauth.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)

    # Store state for later validation
    session['oauth_state'] = state
    print(f"Redirecting to Discord authorization URL with state: {state}")

    return redirect(authorization_url)

@app.route('/callback')
def callback():
    """Handle Discord OAuth callback"""
    if 'discord_id' not in session or 'oauth_state' not in session:
        return render_template('error.html', error="Session expired or invalid. Please try again from Discord.")

    discord_id = session['discord_id']
    print(f"Processing OAuth callback for Discord ID: {discord_id}")

    # Create OAuth2 session
    oauth = OAuth2Session(DISCORD_CLIENT_ID, redirect_uri=DISCORD_REDIRECT_URI, state=session['oauth_state'])

    try:
        # Get token
        token = oauth.fetch_token(
            DISCORD_TOKEN_URL,
            client_secret=DISCORD_CLIENT_SECRET,
            authorization_response=request.url
        )

        # Get user info
        user_response = oauth.get(DISCORD_API_BASE_URL + '/users/@me')
        user_data = user_response.json()

        # Extract user information
        username = user_data.get('username')
        user_id = user_data.get('id')
        email = user_data.get('email')

        print(f"Got Discord user info: {username} ({user_id}) - {email}")

        # Update the discord_id with the one from the API, which is more reliable
        # This fixes issues where the session discord_id might be different from the actual user's Discord ID
        discord_id = user_id
        session['discord_id'] = user_id
        print(f"Updated Discord ID to {discord_id} based on API response")

        if not email:
            return render_template('error.html', error="Email access is required. Please authorize with email access.")

        # Server membership check removed
        # We still get the guilds data for potential future use
        guilds_response = oauth.get(DISCORD_API_BASE_URL + '/users/@me/guilds')
        guilds_data = guilds_response.json()

        # Link user to Pterodactyl
        if pterodactyl_api:
            # Create sanitized username
            sanitized_username = f"{username.lower()}_{user_id}"

            # Check if user already exists
            existing_user = pterodactyl_api.get_user_by_email_sync(email)
            new_account = False
            password = None

            if existing_user:
                print(f"User with email {email} already exists in Pterodactyl. Linking to Discord ID {discord_id}")
                user = existing_user
            else:
                # Generate a random password for new users
                password = secrets.token_urlsafe(12)
                print(f"Creating new Pterodactyl user with email {email} and username {sanitized_username}")
                new_account = True

            # Link Discord user to Pterodactyl
            user = pterodactyl_api.link_discord_to_pterodactyl_sync(
                discord_id,
                email,
                sanitized_username,
                username,
                "Discord",
                password
            )

            if user:
                # Create a more detailed success message
                success_message = "Your Discord account has been successfully linked to your Pterodactyl account!"
                if new_account:
                    success_message = "A new Pterodactyl account has been created and linked to your Discord account!"

                return render_template('success.html',
                                       username=username,
                                       pterodactyl_url=pterodactyl_api.base_url,
                                       new_account=new_account,
                                       password=password,
                                       email=email,
                                       success_message=success_message)
            else:
                return render_template('error.html', error="Failed to link account. Please try again.")
        else:
            return render_template('error.html', error="Pterodactyl API not initialized. Please try again later.")

    except Exception as e:
        print(f"OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('error.html', error=f"Authentication error: {str(e)}")

def start_web_server():
    app.run(host=WEB_HOST, port=WEB_PORT)

def run_web_server_in_thread():
    thread = threading.Thread(target=start_web_server)
    thread.daemon = True
    thread.start()
    return thread
