import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import uuid
import traceback
import requests
from config import DISCORD_BOT_TOKEN, DISCORD_REDIRECT_URI, USER_AUTH_CODES, USER_SERVERS, PTERODACTYL_USERS, SERVER_TEMPLATES
from pterodactyl_api import PterodactylAPI
from web_server import run_web_server_in_thread, set_pterodactyl_api

# Initialize the Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
pterodactyl = PterodactylAPI()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="link", description="Link your Discord account to Pterodactyl Panel")
async def link(interaction: discord.Interaction):
    """Send an authentication link to link Discord account with Pterodactyl Panel"""
    user_id = str(interaction.user.id)

    # Check if user is already linked
    if user_id in PTERODACTYL_USERS:
        # Get the Pterodactyl user ID
        pterodactyl_user_id = PTERODACTYL_USERS[user_id]

        # Try to get user details
        try:
            user_url = f"{pterodactyl.base_url}/api/application/users/{pterodactyl_user_id}"
            user_response = requests.get(user_url, headers=pterodactyl.headers)

            if user_response.status_code == 200:
                user_data = user_response.json()['attributes']

                embed = discord.Embed(
                    title="Account Already Linked",
                    description="Your Discord account is already linked to a Pterodactyl account.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Username", value=user_data['username'], inline=True)
                embed.add_field(name="Email", value=user_data['email'], inline=True)
                embed.add_field(name="Panel URL", value=f"[Access Pterodactyl Panel]({pterodactyl.base_url})", inline=False)

                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except Exception as e:
            print(f"Error getting user details: {e}")

        # Fallback message if we can't get user details
        await interaction.response.send_message(
            "Your Discord account is already linked to a Pterodactyl account. Use `/servers` to see your servers.",
            ephemeral=True
        )
        return

    # Set up the auth URL for OAuth
    oauth_url = f"{DISCORD_REDIRECT_URI.replace('/callback', '')}/oauth?discord_id={user_id}"

    embed = discord.Embed(
        title="🔗 __Link Your Account__",
        description="*Connect your Discord account to the Pterodactyl Panel to create and manage servers.*",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="❗ __Server Membership Required__",
        value="```diff\n+ You must be a member of our Discord server to use this service\n```\nIf you're not already a member, please join the server first.",
        inline=False
    )
    embed.add_field(
        name="📝 __Instructions__",
        value="```md\n1. Click the button below\n2. Authorize with Discord\n3. Your account will be linked automatically\n4. Return to Discord to use bot commands\n```",
        inline=False
    )

    # Create a view with a button for authentication
    view = discord.ui.View()
    button = discord.ui.Button(label="Link with Discord", style=discord.ButtonStyle.primary, url=oauth_url, emoji="🔑")
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Wait to see if the user completes OAuth
    await asyncio.sleep(30)  # Wait 30 seconds

    # Check if the user was linked through OAuth
    if user_id in PTERODACTYL_USERS:
        # Get the Pterodactyl user ID
        pterodactyl_user_id = PTERODACTYL_USERS[user_id]

        # Try to get user details
        try:
            user_url = f"{pterodactyl.base_url}/api/application/users/{pterodactyl_user_id}"
            user_response = requests.get(user_url, headers=pterodactyl.headers)

            if user_response.status_code == 200:
                user_data = user_response.json()['attributes']

                embed = discord.Embed(
                    title="✅ __Account Linked Successfully__",
                    description="*Your Discord account has been linked to your Pterodactyl account!*\n\n```diff\n+ Connection established successfully\n```",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="📝 __Account Information__",
                    value=f"```yaml\nUsername: {user_data['username']}\nEmail: {user_data['email']}\n```",
                    inline=False
                )

                # Create a view with a button for the panel
                view = discord.ui.View()
                panel_button = discord.ui.Button(
                    label="Access Pterodactyl Panel",
                    style=discord.ButtonStyle.link,
                    url=pterodactyl.base_url,
                    emoji="🔗"
                )
                view.add_item(panel_button)

                embed.add_field(
                    name="🚀 __Next Steps__",
                    value="```md\n# Create a Server\nUse /create <template> to create a new server\n\n# View Templates\nUse /templates to see available options\n\n# View Your Servers\nUse /servers to see your existing servers\n```",
                    inline=False
                )

                # Send the message with the button
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                return
        except Exception as e:
            print(f"Error getting user details: {e}")

        # Fallback message if we can't get user details
        embed = discord.Embed(
            title="✅ __Account Linked Successfully__",
            description="*Your Discord account has been linked to your Pterodactyl account!*",
            color=discord.Color.green()
        )

        # Create a view with a button for the panel
        view = discord.ui.View()
        panel_button = discord.ui.Button(
            label="Access Pterodactyl Panel",
            style=discord.ButtonStyle.link,
            url=pterodactyl.base_url,
            emoji="🔗"
        )
        view.add_item(panel_button)

        embed.add_field(
            name="🚀 __Next Steps__",
            value="```md\n# Create a Server\nUse /create <template> to create a new server\n\n# View Templates\nUse /templates to see available options\n```",
            inline=False
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# Define a template autocomplete function
async def template_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocomplete for template names"""
    templates = list(SERVER_TEMPLATES.keys())
    return [
        app_commands.Choice(name=template.capitalize(), value=template)
        for template in templates if current.lower() in template.lower()
    ]

@bot.tree.command(name="create", description="Create a new server with a specified template")
@app_commands.describe(template="The template to use for the server", name="Optional custom name for your server")
@app_commands.autocomplete(template=template_autocomplete)
async def create(interaction: discord.Interaction, template: str, name: str = None):
    """Create a new server based on a template"""
    try:
        user_id = str(interaction.user.id)
        print(f"User {user_id} ({interaction.user.name}) is attempting to create a server with template '{template}'")

        # Check if the user is linked to a Pterodactyl account
        if user_id not in PTERODACTYL_USERS:
            await interaction.response.send_message(
                "You need to link your account first. Use `/link` to get started.",
                ephemeral=True
            )
            return

        # Check if the template exists
        if template not in SERVER_TEMPLATES:
            # Create a list of available templates with their details
            template_list = ""
            for temp_name, temp_data in SERVER_TEMPLATES.items():
                template_list += f"**{temp_name}**: {temp_data['description']} - RAM: {temp_data['memory']}MB, CPU: {temp_data['cpu']/100} cores, Disk: {temp_data['disk']/1024}GB\n"

            embed = discord.Embed(
                title="Template Not Found",
                description=f"Template '{template}' not found. Please choose from the available templates:",
                color=discord.Color.red()
            )
            embed.add_field(name="Available Templates", value=template_list, inline=False)
            embed.set_footer(text="Use /templates to see all available templates")

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Sync the user's servers first and check if they can create more
        await pterodactyl.sync_user_servers(user_id)

        # Check if the user can create more servers
        if not await pterodactyl.can_create_server(user_id):
            await interaction.response.send_message(
                "You have reached the maximum number of servers (2). Please delete a server before creating a new one. Use `/delete <server_id>` to delete a server.",
                ephemeral=True
            )
            return

        # Generate server name if not provided
        server_name = name if name else f"{template}-{interaction.user.name}"
        # Remove spaces and special characters from server name
        server_name = ''.join(c for c in server_name if c.isalnum() or c in '-_')

        # Show the template details before creating
        template_data = SERVER_TEMPLATES[template]
        embed = discord.Embed(
            title=f"Creating {template_data['name']}",
            description=f"**{template_data['description']}**\n\nCreating your server with the following specifications:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Server Name", value=server_name)
        embed.add_field(name="RAM", value=f"{template_data['memory']}MB")
        embed.add_field(name="CPU", value=f"{template_data['cpu']/100} cores")
        embed.add_field(name="Disk", value=f"{template_data['disk']/1024}GB")
        embed.set_footer(text="Server creation in progress... This may take a moment.")

        # Send initial message
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Create the server
        pterodactyl_user_id = PTERODACTYL_USERS[user_id]
        print(f"Creating server for Pterodactyl user ID: {pterodactyl_user_id}")

        # Update the embed with progress
        embed.description = f"**{template_data['description']}**\n\n**Status:** Finding available node and allocation..."
        await interaction.edit_original_response(embed=embed)

        # Update the embed with progress
        embed.description = f"**{template_data['description']}**\n\n**Status:** Configuring server settings..."
        await interaction.edit_original_response(embed=embed)

        server, error = await pterodactyl.create_server(pterodactyl_user_id, template, server_name)

        if server:
            try:
                # Register the server for the user
                await pterodactyl.register_server_for_user(user_id, server['id'])
                print(f"Server created successfully with ID: {server['id']} for user {user_id}")

                # Get server name (with fallback)
                server_name = server.get('name', server_name)

                # Update the embed with success information
                embed = discord.Embed(
                    title="Server Created Successfully",
                    description=f"Your new server '{server_name}' has been created!",
                    color=discord.Color.green()
                )

                # Add server ID if available
                if 'identifier' in server:
                    embed.add_field(name="Server ID", value=server['identifier'])
                elif 'uuid' in server:
                    embed.add_field(name="Server ID", value=server['uuid'])
                else:
                    embed.add_field(name="Server ID", value=server['id'])

                embed.add_field(name="Template", value=template)

                # Add server details
                if 'allocation' in server:
                    allocation = server['allocation']
                    # Check if allocation is a dictionary or just an ID
                    if isinstance(allocation, dict):
                        # Prefer alias over IP address
                        alias = allocation.get('alias')
                        ip = allocation.get('ip', 'Unknown')
                        port = allocation.get('port', 'Unknown')

                        # Use alias if available, otherwise use IP
                        connection_host = alias if alias else ip
                        connection_info = f"{connection_host}:{port}"
                        embed.add_field(name="Connection Info", value=f"`{connection_info}`", inline=False)
                    else:
                        # Try to get allocation details from the API
                        try:
                            allocation_details = pterodactyl.get_allocation_sync(allocation)
                            if allocation_details:
                                # Prefer alias over IP address
                                alias = allocation_details.get('alias')
                                ip = allocation_details.get('ip', 'Unknown')
                                port = allocation_details.get('port', 'Unknown')

                                # Use alias if available, otherwise use IP
                                connection_host = alias if alias else ip
                                connection_info = f"{connection_host}:{port}"
                                embed.add_field(name="Connection Info", value=f"`{connection_info}`", inline=False)
                        except Exception as e:
                            print(f"Error getting allocation details: {e}")
                            embed.add_field(name="Connection Info", value="Check panel for connection details", inline=False)

                # Get server identifier (with fallback)
                server_identifier = server.get('identifier', server.get('uuid', server.get('id', 'unknown')))

                # Add panel URL
                panel_url = f"{pterodactyl.base_url}/server/{server_identifier}"
                embed.add_field(name="Panel URL", value=f"[Access your server]({panel_url})", inline=False)
                embed.set_footer(text="Your server is now being installed. It may take a few minutes before it's ready to use.")

                # Update the original message with the success embed
                await interaction.edit_original_response(embed=embed)
            except Exception as e:
                print(f"Exception handling server creation success: {str(e)}")
                traceback.print_exc()

                # Update with a simplified success message
                simple_embed = discord.Embed(
                    title="Server Created Successfully",
                    description=f"Your new server has been created! You can access it from the Pterodactyl panel.",
                    color=discord.Color.green()
                )
                simple_embed.add_field(name="Panel URL", value=f"[Access Pterodactyl Panel]({pterodactyl.base_url})", inline=False)

                await interaction.edit_original_response(embed=simple_embed)
        else:
            print(f"Server creation failed for user {user_id}: {error}")
            error_embed = discord.Embed(
                title="Server Creation Failed",
                description=f"Failed to create server: {error}",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="What to do next",
                value="Please try again later or contact an administrator for assistance.",
                inline=False
            )
            await interaction.edit_original_response(embed=error_embed)
    except Exception as e:
        print(f"Exception in create command: {str(e)}")
        await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="servers", description="List your servers")
async def servers(interaction: discord.Interaction):
    """List all servers owned by the user"""
    user_id = str(interaction.user.id)

    # Check if the user is linked to a Pterodactyl account
    if user_id not in PTERODACTYL_USERS:
        await interaction.response.send_message(
            "You need to link your account first. Use `/link` to get started.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Sync the user's servers first
    await pterodactyl.sync_user_servers(user_id)

    # Get the user's servers
    pterodactyl_user_id = PTERODACTYL_USERS[user_id]
    servers = await pterodactyl.get_user_servers(pterodactyl_user_id)

    if servers:
        embed = discord.Embed(
            title="🖥️ __Your Servers__",
            description=f"You have **{len(servers)}** server(s) out of a maximum of **2**",
            color=discord.Color.blue()
        )

        # Add user information
        try:
            user_url = f"{pterodactyl.base_url}/api/application/users/{pterodactyl_user_id}"
            user_response = requests.get(user_url, headers=pterodactyl.headers)

            if user_response.status_code == 200:
                user_data = user_response.json()['attributes']
                embed.add_field(
                    name="📝 __Account Information__",
                    value=f"```md\n# Username: {user_data['username']}\n# Email: {user_data['email']}\n```",
                    inline=False
                )
        except Exception as e:
            print(f"Error getting user details: {e}")

        # Add server information
        for i, server in enumerate(servers):
            # Get server status with emoji
            status = server.get('status')
            if status is None or status == 'offline':
                status_emoji = "🔴"
                status_text = "Offline"
            elif status == 'running':
                status_emoji = "🟢"
                status_text = "Online"
            else:
                status_emoji = "🟠"
                status_text = status.capitalize()

            # Get server identifier
            server_id = server.get('identifier', server.get('uuid', server.get('id', 'Unknown')))

            # Get connection info
            connection_info = "Check panel for details"
            if 'allocation' in server:
                allocation = server['allocation']
                if isinstance(allocation, dict):
                    # Prefer alias over IP address
                    alias = allocation.get('alias')
                    ip = allocation.get('ip', 'Unknown')
                    port = allocation.get('port', 'Unknown')

                    # Use alias if available, otherwise use IP
                    connection_host = alias if alias else ip
                    connection_info = f"{connection_host}:{port}"
                else:
                    # Try to get allocation details from the API
                    try:
                        allocation_details = pterodactyl.get_allocation_sync(allocation)
                        if allocation_details:
                            # Prefer alias over IP address
                            alias = allocation_details.get('alias')
                            ip = allocation_details.get('ip', 'Unknown')
                            port = allocation_details.get('port', 'Unknown')

                            # Use alias if available, otherwise use IP
                            connection_host = alias if alias else ip
                            connection_info = f"{connection_host}:{port}"
                    except Exception as e:
                        print(f"Error getting allocation details: {e}")

            # Get server resources
            memory = server.get('limits', {}).get('memory', 'Unknown')
            disk = server.get('limits', {}).get('disk', 'Unknown')
            cpu = server.get('limits', {}).get('cpu', 'Unknown')

            # Format memory and disk
            if isinstance(memory, (int, float)):
                memory_formatted = f"{memory} MB" if memory < 1024 else f"{memory/1024:.1f} GB"
            else:
                memory_formatted = "Unknown"

            if isinstance(disk, (int, float)):
                disk_formatted = f"{disk} MB" if disk < 1024 else f"{disk/1024:.1f} GB"
            else:
                disk_formatted = "Unknown"

            if isinstance(cpu, (int, float)):
                cpu_formatted = f"{cpu/100:.1f} cores"
            else:
                cpu_formatted = "Unknown"

            # Create server panel URL
            panel_url = f"{pterodactyl.base_url}/server/{server_id}"

            # Add server field with improved formatting
            server_info = (
                f"```ini\n"
                f"[Status]    {status_emoji} {status_text}\n"
                f"[Connect]   {connection_info}\n"
                f"[Resources] {memory_formatted} RAM | {disk_formatted} Disk | {cpu_formatted}\n"
                f"[ID]        {server_id}\n"
                f"```\n"
                f"**[➡️ Access Server]({panel_url})**"
            )

            embed.add_field(
                name=f"🎮 __**{server['name']}**__",
                value=server_info,
                inline=True
            )

        # Add a note about how to create more servers and delete servers
        if len(servers) < 2:
            embed.add_field(
                name="💬 __Available Commands__",
                value=f"```md\n# /delete - Delete a server\n# /create <template> - Create a new server\n# /templates - View available templates\n```",
                inline=False
            )
            embed.set_footer(text=f"✨ You can create {2 - len(servers)} more server(s) out of a maximum of 2.")
        else:
            embed.add_field(
                name="💬 __Available Commands__",
                value=f"```md\n# /delete - Delete a server\n# /templates - View available templates\n```",
                inline=False
            )
            embed.set_footer(text="⚠️ You have reached the maximum number of servers.")

        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="🔍 __No Servers Found__",
            description="*You don't have any servers yet.*",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🚀 __Getting Started__",
            value="```md\n# Step 1: View available templates\nUse the /templates command to see what's available\n\n# Step 2: Create your first server\nUse /create <template> to launch your server\n```",
            inline=False
        )
        embed.set_footer(text="✨ You can create up to 2 servers with your account.")
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="delete", description="Delete one of your servers")
async def delete_server(interaction: discord.Interaction):
    """Delete a server - shows a list of your servers to choose from"""
    user_id = str(interaction.user.id)

    # Check if the user is linked to a Pterodactyl account
    if user_id not in PTERODACTYL_USERS:
        await interaction.response.send_message(
            "You need to link your account first. Use `/link` to get started.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Sync the user's servers first
    await pterodactyl.sync_user_servers(user_id)

    # Get the user's servers
    pterodactyl_user_id = PTERODACTYL_USERS[user_id]
    servers = await pterodactyl.get_user_servers(pterodactyl_user_id)

    # Show the list of servers
    if not servers:
        await interaction.followup.send(
            "You don't have any servers to delete.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🖥️ __Select Server to Delete__",
        description="*Click the button below the server you want to remove.*",
        color=discord.Color.red()
    )

    # Create a view with buttons for each server
    view = discord.ui.View(timeout=120)

    # Add server information to the embed
    for server in servers:
        # Get server identifier (the one used in the panel URL)
        server_identifier = server.get('identifier', server.get('uuid', server.get('id', 'Unknown')))
        server_name = server['name']
        server_id = server['id']

        # Format the server information
        embed.add_field(
            name=f"🎮 __**{server_name}**__",
            value=f"```yaml\nPanel ID: {server_identifier}\nInternal ID: {server_id}\n```",
            inline=True
        )

        # Add a button for this server
        button = discord.ui.Button(label=f"Delete {server_name}", style=discord.ButtonStyle.danger, custom_id=f"delete_{server_id}")

        # Define the callback for this button
        async def button_callback(interaction, server_id=server_id, server_name=server_name):
            # Create confirmation embed
            confirm_embed = discord.Embed(
                title="⚠️ __Confirm Server Deletion__",
                description=f"**Are you sure you want to delete:**\n\n```fix\n{server_name}\n```\n*This action cannot be undone.*",
                color=discord.Color.red()
            )

            # Create confirmation buttons
            confirm_view = discord.ui.View(timeout=60)
            confirm_button = discord.ui.Button(label="Confirm Delete", style=discord.ButtonStyle.danger, custom_id=f"confirm_{server_id}")
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel")

            async def confirm_callback(interaction):
                # Delete the server
                success = await pterodactyl.delete_server(server_id, user_id)

                if success:
                    success_embed = discord.Embed(
                        title="✅ __Server Deleted Successfully__",
                        description=f"Your server **{server_name}** has been removed from your account.",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(
                        name="🚀 __Next Steps__",
                        value="```md\n# Create a New Server\nUse /create <template> to create a new server\n\n# View Templates\nUse /templates to see available options\n```",
                        inline=False
                    )
                    await interaction.response.edit_message(embed=success_embed, view=None)
                else:
                    error_embed = discord.Embed(
                        title="❌ __Error Deleting Server__",
                        description=f"```diff\n- Failed to delete server: {server_name}\n```\n*Please try again later or contact an administrator.*",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=None)

            async def cancel_callback(interaction):
                cancel_embed = discord.Embed(
                    title="❌ __Operation Cancelled__",
                    description="*Server deletion has been cancelled.*\n\n```ini\n[Your server remains unchanged]\n```",
                    color=discord.Color.orange()
                )
                await interaction.response.edit_message(embed=cancel_embed, view=None)

            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback

            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)

            await interaction.response.edit_message(embed=confirm_embed, view=confirm_view)

        button.callback = button_callback
        view.add_item(button)

    # Add a note about the IDs
    embed.add_field(
        name="📝 __ID Information__",
        value="```md\n# Panel ID\nThis is what you see in the URL when accessing your server\n\n# Internal ID\nThis is used by the system for reference\n```",
        inline=False
    )
    embed.set_footer(text="⚠️ Deleting a server is permanent and cannot be undone.")

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="templates", description="List available server templates")
async def templates(interaction: discord.Interaction):
    """List all available server templates"""
    embed = discord.Embed(
        title="📎 __Available Server Templates__",
        description="*Select a template that fits your needs to create a new server.*\n\n**To create a server:** `/create <template>`",
        color=discord.Color.blue()
    )

    # Add user information if linked
    user_id = str(interaction.user.id)
    if user_id in PTERODACTYL_USERS:
        # Sync the user's servers first
        await pterodactyl.sync_user_servers(user_id)

        pterodactyl_user_id = PTERODACTYL_USERS[user_id]
        servers = await pterodactyl.get_user_servers(pterodactyl_user_id)
        servers_count = len(servers) if servers else 0
        servers_remaining = max(0, 2 - servers_count)

        embed.add_field(
            name="📊 __Your Server Quota__",
            value=f"```yaml\nCurrent Servers: {servers_count}/2\nRemaining Slots: {servers_remaining}\n```",
            inline=False
        )

    # Add template information
    for template_name, template_data in SERVER_TEMPLATES.items():
        # Format memory and disk
        memory = template_data['memory']
        disk = template_data['disk']
        cpu = template_data['cpu']

        memory_formatted = f"{memory} MB" if memory < 1024 else f"{memory/1024:.1f} GB"
        disk_formatted = f"{disk} MB" if disk < 1024 else f"{disk/1024:.1f} GB"
        cpu_formatted = f"{cpu/100:.1f} cores"

        # Get emoji based on template name
        emoji = "💻"  # Default computer emoji
        if "minecraft" in template_name.lower():
            emoji = "⛏️"  # Pickaxe for Minecraft
        elif "python" in template_name.lower():
            emoji = "🐍"  # Snake for Python
        elif "node" in template_name.lower() or "javascript" in template_name.lower():
            emoji = "🐛"  # Bug for JavaScript (Node.js)
        elif "web" in template_name.lower() or "html" in template_name.lower():
            emoji = "🌐"  # Globe for web servers
        elif "game" in template_name.lower():
            emoji = "🎮"  # Game controller for game servers
        elif "database" in template_name.lower() or "sql" in template_name.lower():
            emoji = "📂"  # Folder for databases
        elif "large" in template_name.lower():
            emoji = "💪"  # Strong arm for large templates
        elif "small" in template_name.lower():
            emoji = "🤷"  # Person shrugging for small templates
        elif "medium" in template_name.lower():
            emoji = "🔸"  # Medium circle for medium templates

        # Format the template information
        template_info = f"*{template_data['description']}*\n\n"
        template_info += f"```ini\n"
        template_info += f"[RAM]  {memory_formatted}\n"
        template_info += f"[CPU]  {cpu_formatted}\n"
        template_info += f"[Disk] {disk_formatted}\n"
        template_info += f"```\n"
        template_info += f"**Create with:** `/create {template_name}`"

        embed.add_field(
            name=f"{emoji} __**{template_name.capitalize()}**__",
            value=template_info,
            inline=True
        )

    embed.set_footer(text="✨ Choose a template that best fits your project requirements.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="reset-password", description="Reset your Pterodactyl panel password")
async def reset_password(interaction: discord.Interaction):
    """Reset your Pterodactyl panel password"""
    user_id = str(interaction.user.id)

    # Check if the user is linked to a Pterodactyl account
    if user_id not in PTERODACTYL_USERS:
        await interaction.response.send_message(
            "You need to link your account first. Use `/link` to get started.",
            ephemeral=True
        )
        return

    # Show initial message
    embed = discord.Embed(
        title="🔑 __Password Reset in Progress__",
        description="*Resetting your Pterodactyl panel password...*\n\n```yaml\nStatus: Processing\n```",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Get the Pterodactyl user ID
    pterodactyl_user_id = PTERODACTYL_USERS[user_id]

    # Get user details if possible
    try:
        user_url = f"{pterodactyl.base_url}/api/application/users/{pterodactyl_user_id}"
        user_response = requests.get(user_url, headers=pterodactyl.headers)

        if user_response.status_code == 200:
            user_data = user_response.json()['attributes']
            username = user_data['username']
            email = user_data['email']
        else:
            username = "Unknown"
            email = "Unknown"
    except Exception as e:
        print(f"Error getting user details: {e}")
        username = "Unknown"
        email = "Unknown"

    # Reset the password
    new_password = await pterodactyl.reset_user_password(pterodactyl_user_id)

    if new_password:
        success_embed = discord.Embed(
            title="🔓 __Password Reset Successful__",
            description="*Your Pterodactyl panel password has been reset successfully.*\n\n```diff\n+ New credentials are ready to use\n```",
            color=discord.Color.green()
        )

        # Add user information
        if username != "Unknown" and email != "Unknown":
            success_embed.add_field(
                name="📝 __Account Information__",
                value=f"```yaml\nUsername: {username}\nEmail: {email}\n```",
                inline=False
            )

        # Add password field with styling
        success_embed.add_field(
            name="🅰️ __New Password__",
            value=f"```fix\n{new_password}\n```",
            inline=False
        )

        success_embed.add_field(
            name="⚠️ __IMPORTANT SECURITY NOTICE__",
            value="**Please save this password immediately!**\n\n• This password will **not** be shown again\n• You will need it to log in to the Pterodactyl Panel\n• For security, change this password after logging in",
            inline=False
        )

        success_embed.add_field(
            name="🔗 __Access Your Panel__",
            value=f"**[Click Here to Log In to Pterodactyl Panel]({pterodactyl.base_url})**",
            inline=False
        )

        success_embed.set_footer(text="⚠️ Never share your password with anyone, including server administrators.")

        await interaction.edit_original_response(embed=success_embed)
    else:
        error_embed = discord.Embed(
            title="❌ __Password Reset Failed__",
            description="*We encountered an issue while trying to reset your password.*\n\n```diff\n- Unable to complete password reset\n```",
            color=discord.Color.red()
        )
        error_embed.add_field(
            name="🔍 __Troubleshooting Steps__",
            value="```md\n# Wait a few minutes and try again\n# Check your connection to the server\n# Contact an administrator if the issue persists\n```",
            inline=False
        )
        await interaction.edit_original_response(embed=error_embed)

@bot.tree.command(name="panel-info", description="Get information about the Pterodactyl panel configuration")
async def panel_info(interaction: discord.Interaction):
    """Get information about the Pterodactyl panel configuration"""
    # Only allow administrators to use this command
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("This command is only available to administrators.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # Get nests
        nests = await pterodactyl.get_nests()

        if not nests:
            await interaction.followup.send("No nests found on the Pterodactyl panel.", ephemeral=True)
            return

        # Create an embed for the panel information
        embed = discord.Embed(
            title="💻 __Pterodactyl Panel Configuration__",
            description=f"*System information for administrators*\n\n**Panel URL:** `{PTERODACTYL_URL}`",
            color=discord.Color.blue()
        )

        # Get configured eggs from SERVER_TEMPLATES
        configured_eggs = {}
        for template_name, template_data in SERVER_TEMPLATES.items():
            nest_id = template_data.get('nest')
            egg_id = template_data.get('egg')
            if nest_id and egg_id:
                if nest_id not in configured_eggs:
                    configured_eggs[nest_id] = []
                if egg_id not in configured_eggs[nest_id]:
                    configured_eggs[nest_id].append(egg_id)

        # Add nest information (only configured ones)
        nest_info = "```yaml\n"
        for nest in nests:
            nest_attr = nest['attributes']
            nest_id = nest_attr['id']

            # Only show nests that have configured eggs
            if nest_id in configured_eggs:
                nest_info += f"# {nest_attr['name']} (ID: {nest_id})\n"

                # Get eggs for this nest
                eggs = await pterodactyl.get_eggs(nest_id)
                if eggs:
                    found_eggs = False
                    for egg in eggs:
                        egg_attr = egg['attributes']
                        egg_id = egg_attr['id']

                        # Only show eggs that are configured in SERVER_TEMPLATES
                        if egg_id in configured_eggs[nest_id]:
                            found_eggs = True
                            # Find which template uses this egg
                            template_names = []
                            for template_name, template_data in SERVER_TEMPLATES.items():
                                if template_data.get('nest') == nest_id and template_data.get('egg') == egg_id:
                                    template_names.append(template_name)

                            template_str = f" (Used in: {', '.join(template_names)})" if template_names else ""
                            nest_info += f"  - {egg_attr['name']} (ID: {egg_id}){template_str}\n"

                    if not found_eggs:
                        nest_info += "  - No configured eggs found for this nest\n"
                else:
                    nest_info += "  - No eggs found for this nest\n"
        nest_info += "```"

        embed.add_field(name="🐥 __Configured Nests and Eggs__", value=nest_info, inline=False)

        # Get nodes
        nodes = await pterodactyl.get_nodes()
        if nodes:
            node_info = "```ini\n"
            for node in nodes:
                node_attr = node['attributes']
                node_info += f"[{node_attr['name']}] (ID: {node_attr['id']})\n"
                node_info += f"  Location = {node_attr['location_id']}\n"
                memory_formatted = f"{node_attr['memory']} MB" if node_attr['memory'] < 1024 else f"{node_attr['memory']/1024:.1f} GB"
                disk_formatted = f"{node_attr['disk']} MB" if node_attr['disk'] < 1024 else f"{node_attr['disk']/1024:.1f} GB"
                node_info += f"  Memory = {memory_formatted}\n"
                node_info += f"  Disk = {disk_formatted}\n\n"
            node_info += "```"

            embed.add_field(name="💻 __Available Nodes__", value=node_info, inline=False)
        else:
            embed.add_field(name="💻 __Available Nodes__", value="```diff\n- No nodes found\n```", inline=False)

        # Get locations
        locations = await pterodactyl.get_locations()
        if locations:
            location_info = "```md\n"
            for location in locations:
                location_attr = location['attributes']
                location_info += f"# {location_attr['short']} (ID: {location_attr['id']})\n"
                location_info += f"  {location_attr['long']}\n\n"
            location_info += "```"

            embed.add_field(name="📍 __Available Locations__", value=location_info, inline=False)
        else:
            embed.add_field(name="📍 __Available Locations__", value="```diff\n- No locations found\n```", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Error in panel-info command: {str(e)}")
        traceback.print_exc()
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

def main():
    # Pass the pterodactyl API instance to the web server
    set_pterodactyl_api(pterodactyl)

    # Start the web server in a separate thread
    web_thread = run_web_server_in_thread()

    # Start the Discord bot
    bot.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    main()
