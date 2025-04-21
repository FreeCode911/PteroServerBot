import requests
import json
import asyncio
import uuid
import random
import secrets
import traceback
from config import PTERODACTYL_URL, PTERODACTYL_API_KEY, SERVER_TEMPLATES, USER_SERVERS, PTERODACTYL_USERS
import persistence

class PterodactylAPI:
    def __init__(self):
        self.base_url = PTERODACTYL_URL.rstrip('/')
        self.api_key = PTERODACTYL_API_KEY
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

    async def create_user(self, username, email, first_name, last_name, password=None):
        """Create a new user in Pterodactyl Panel"""
        if password is None:
            password = str(uuid.uuid4())  # Generate a random password if none provided

        url = f"{self.base_url}/api/application/users"
        payload = {
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
        }

        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code == 201:
            return response.json()['attributes']
        else:
            print(f"Error creating user: {response.text}")
            return None

    async def get_user_by_email(self, email):
        """Get a user by email - async version"""
        url = f"{self.base_url}/api/application/users"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            users = response.json()['data']
            for user in users:
                if user['attributes']['email'] == email:
                    return user['attributes']

        return None

    def get_user_by_email_sync(self, email):
        """Get a user by email - sync version"""
        try:
            url = f"{self.base_url}/api/application/users"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                users = response.json()['data']
                for user in users:
                    if user['attributes']['email'] == email:
                        return user['attributes']

            return None
        except Exception as e:
            print(f"Error getting user by email: {str(e)}")
            return None

    async def create_server(self, user_id, template_name, server_name=None):
        """Create a new server for a user based on a template with automatic allocation"""
        try:
            if template_name not in SERVER_TEMPLATES:
                return None, "Template not found"

            template = SERVER_TEMPLATES[template_name]

            if server_name is None:
                server_name = f"{template_name}-{str(uuid.uuid4())[:8]}"

            print(f"Creating server '{server_name}' for user {user_id} with template {template_name}")

            # Find an available node and allocation
            node_allocation = await self.find_available_node_and_allocation()

            if not node_allocation:
                return None, "No available allocations found. Please contact an administrator."

            node = node_allocation['node']
            allocation = node_allocation['allocation']

            print(f"Found node {node['id']} and allocation {allocation['id']} ({allocation['ip']}:{allocation['port']})")

            # Get the nest and egg details
            nest_id = template.get('nest', 1)  # Default to nest ID 1 if not specified
            egg_id = template.get('egg', 1)    # Default to egg ID 1 if not specified

            # Use the node's location
            location_id = node['location_id']

            # Get egg details to ensure we have the correct environment variables and startup command
            egg_details = await self.get_egg_details(nest_id, egg_id)

            if not egg_details:
                return None, f"Could not find egg with ID {egg_id} in nest {nest_id}"

            # Get the correct docker image and startup command from the egg
            docker_image = egg_details.get('docker_image', "ghcr.io/pterodactyl/yolks:java_17")
            startup_command = egg_details.get('startup', "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar {{SERVER_JARFILE}}")

            # Get the environment variables from the egg
            environment_vars = {}

            # Check if we have variables in the egg details
            egg_variables = egg_details.get('relationships', {}).get('variables', {}).get('data', [])
            if egg_variables:
                print(f"Found {len(egg_variables)} variables for egg {egg_id}")

                # Get detailed variable information for all variables from the egg
                for var_data in egg_variables:
                    var_attr = var_data.get('attributes', {})
                    env_name = var_attr.get('env_variable')
                    env_default = var_attr.get('default_value')
                    env_required = var_attr.get('required', False)

                    print(f"Variable: {env_name}, Default: {env_default}, Required: {env_required}")

                    if env_name:
                        environment_vars[env_name] = env_default or ''

            # If no environment variables were found in the egg, log a warning
            if not environment_vars:
                print("No environment variables found in egg relationships")

            # If still no environment variables were found, use some basic defaults based on egg type
            if not environment_vars:
                egg_name = egg_details.get('name', '').lower()
                print(f"No environment variables found. Using basic defaults for egg type: {egg_name}")

                if 'python' in egg_name:
                    environment_vars = {
                        "USER_UPLOAD": "0",
                        "AUTO_UPDATE": "0",
                        "PY_FILE": "main.py",
                        "REQUIREMENTS_FILE": "requirements.txt",
                        "STARTUP_CMD": "python"
                    }
                elif 'minecraft' in egg_name:
                    environment_vars = {
                        "SERVER_JARFILE": "server.jar",
                        "MINECRAFT_VERSION": "latest",
                        "BUILD_NUMBER": "latest",
                        "VANILLA_VERSION": "latest"
                    }
                elif 'node' in egg_name or 'javascript' in egg_name:
                    environment_vars = {
                        "USER_UPLOAD": "0",
                        "AUTO_UPDATE": "0",
                        "JS_FILE": "index.js",
                        "NODE_PACKAGES": ""
                    }
                else:
                    # Generic fallback
                    environment_vars = {
                        "USER_UPLOAD": "0",
                        "AUTO_UPDATE": "0"
                    }

            # Apply template-specific environment variables if available
            if 'env' in template:
                print(f"Applying template-specific environment variables: {template['env']}")
                for key, value in template['env'].items():
                    environment_vars[key] = value

            url = f"{self.base_url}/api/application/servers"
            payload = {
                "name": server_name,
                "description": f"Server created with {template_name} template via Discord bot",
                "user": user_id,
                "egg": egg_id,
                "docker_image": docker_image,
                "startup": startup_command,
                "environment": environment_vars,
                "limits": {
                    "memory": template['memory'],
                    "swap": 0,
                    "disk": template['disk'],
                    "io": 500,
                    "cpu": template['cpu']
                },
                "feature_limits": {
                    "databases": 1,
                    "backups": 1,
                    "allocations": 1
                },
                "allocation": {
                    "default": allocation['id']
                },
                "start_on_completion": True,
                "skip_scripts": False,
                "oom_disabled": True
            }

            print(f"Sending server creation request with payload: {json.dumps(payload, indent=2)}")

            response = requests.post(url, headers=self.headers, json=payload)

            if response.status_code == 201:
                server_data = response.json()['attributes']
                print(f"Server created successfully with ID: {server_data['id']}")
                return server_data, None
            else:
                error_message = f"Error creating server: {response.status_code} - {response.text}"
                print(error_message)
                return None, error_message
        except Exception as e:
            error_message = f"Exception creating server: {str(e)}"
            print(error_message)
            return None, error_message

    async def get_nests(self):
        """Get all nests"""
        try:
            url = f"{self.base_url}/api/application/nests"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()['data']
            else:
                print(f"Error getting nests: {response.text}")
                return []
        except Exception as e:
            print(f"Exception getting nests: {str(e)}")
            return []

    async def get_eggs(self, nest_id):
        """Get all eggs for a nest"""
        try:
            url = f"{self.base_url}/api/application/nests/{nest_id}/eggs"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()['data']
            else:
                print(f"Error getting eggs: {response.text}")
                return []
        except Exception as e:
            print(f"Exception getting eggs: {str(e)}")
            return []

    async def get_egg_details(self, nest_id, egg_id):
        """Get details for a specific egg"""
        try:
            url = f"{self.base_url}/api/application/nests/{nest_id}/eggs/{egg_id}?include=variables"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()['attributes']
            else:
                print(f"Error getting egg details: {response.text}")
                # Try to get all eggs to see what's available
                print("Attempting to list available eggs:")
                eggs = await self.get_eggs(nest_id)
                if eggs:
                    print(f"Available eggs for nest {nest_id}:")
                    for egg in eggs:
                        print(f"  - ID: {egg['attributes']['id']}, Name: {egg['attributes']['name']}")
                else:
                    print(f"No eggs found for nest {nest_id}")
                    # Try to list all nests
                    nests = await self.get_nests()
                    if nests:
                        print("Available nests:")
                        for nest in nests:
                            print(f"  - ID: {nest['attributes']['id']}, Name: {nest['attributes']['name']}")
                    else:
                        print("No nests found")
                return None
        except Exception as e:
            print(f"Exception getting egg details: {str(e)}")
            traceback.print_exc()
            return None

    async def get_egg_variable(self, nest_id, egg_id, variable_id):
        """Get details for a specific egg variable"""
        try:
            url = f"{self.base_url}/api/application/nests/{nest_id}/eggs/{egg_id}/variables/{variable_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response.json()['attributes']
            else:
                print(f"Error getting egg variable details: {response.text}")
                return None
        except Exception as e:
            print(f"Exception getting egg variable details: {str(e)}")
            return None

    async def get_user_servers(self, user_id):
        """Get all servers for a user"""
        url = f"{self.base_url}/api/application/servers"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            servers = response.json()['data']
            user_servers = []

            for server in servers:
                if server['attributes']['user'] == user_id:
                    user_servers.append(server['attributes'])

            return user_servers
        else:
            print(f"Error getting servers: {response.text}")
            return []

    async def link_discord_to_pterodactyl(self, discord_id, email, username, first_name="Discord", last_name="User"):
        """Link a Discord user to a Pterodactyl user (create if doesn't exist) - async version"""
        # Check if user already exists
        user = await self.get_user_by_email(email)

        if not user:
            # Create new user
            user = await self.create_user(username, email, first_name, last_name)

        if user:
            # Store the link in our database
            PTERODACTYL_USERS[discord_id] = user['id']
            # Save the updated data to disk
            persistence.save_pterodactyl_users(PTERODACTYL_USERS)
            print(f"Saved link between Discord user {discord_id} and Pterodactyl user {user['id']}")
            return user

        return None

    def link_discord_to_pterodactyl_sync(self, discord_id, email, username, first_name="Discord", last_name="User", password=None):
        """Link a Discord user to a Pterodactyl user (create if doesn't exist) - sync version for web server"""
        try:
            # Check if user already exists
            user = self.get_user_by_email_sync(email)

            if not user:
                # Create new user
                if not username:
                    username = f"discord_{discord_id}"

                if not password:
                    password = str(uuid.uuid4())  # Generate a random password if none provided

                url = f"{self.base_url}/api/application/users"
                payload = {
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "password": password,
                }

                print(f"Creating new user with payload: {payload}")
                response = requests.post(url, headers=self.headers, json=payload)

                if response.status_code == 201:
                    user = response.json()['attributes']
                    print(f"Created new user with ID: {user['id']}")
                else:
                    print(f"Error creating user: {response.text}")
                    return None
            else:
                print(f"Found existing user with ID: {user['id']}")

            if user:
                # Store the link in our database
                PTERODACTYL_USERS[discord_id] = user['id']
                # Save the updated data to disk
                persistence.save_pterodactyl_users(PTERODACTYL_USERS)
                print(f"Linked Discord user {discord_id} to Pterodactyl user {user['id']} and saved to disk")
                return user

            return None
        except Exception as e:
            print(f"Error linking Discord to Pterodactyl: {str(e)}")
            traceback.print_exc()
            return None

    async def check_server_owner(self, server_id, discord_id):
        """Check if the user is the owner of the server"""
        try:
            # Get server details
            url = f"{self.base_url}/api/application/servers/{server_id}"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                server_data = response.json()['attributes']
                pterodactyl_user_id = PTERODACTYL_USERS.get(discord_id)

                # Check if the user is the owner
                if pterodactyl_user_id and server_data['user'] == pterodactyl_user_id:
                    return True, server_data
                else:
                    return False, None
            else:
                print(f"Error getting server details: {response.status_code} - {response.text}")
                return False, None
        except Exception as e:
            print(f"Exception checking server owner: {str(e)}")
            traceback.print_exc()
            return False, None

    async def delete_server(self, server_id, discord_id=None):
        """Delete a server from the Pterodactyl panel"""
        try:
            # If discord_id is provided, verify ownership
            if discord_id:
                is_owner, _ = await self.check_server_owner(server_id, discord_id)
                if not is_owner:
                    print(f"User {discord_id} is not the owner of server {server_id}")
                    return False

            url = f"{self.base_url}/api/application/servers/{server_id}"
            response = requests.delete(url, headers=self.headers)

            if response.status_code == 204:
                print(f"Server {server_id} deleted successfully")

                # Remove the server from all users' server lists
                for user_id, server_list in USER_SERVERS.items():
                    if server_id in server_list:
                        USER_SERVERS[user_id].remove(server_id)
                        print(f"Removed server {server_id} from user {user_id}'s server list")

                # Save the updated data to disk
                persistence.save_user_servers(USER_SERVERS)
                print(f"Saved updated user servers data to disk after deleting server {server_id}")

                return True
            else:
                print(f"Error deleting server: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Exception deleting server: {str(e)}")
            traceback.print_exc()
            return False

    async def sync_user_servers(self, discord_id):
        """Sync the user's servers with the Pterodactyl panel"""
        try:
            if discord_id not in PTERODACTYL_USERS:
                return False

            pterodactyl_user_id = PTERODACTYL_USERS[discord_id]
            servers = await self.get_user_servers(pterodactyl_user_id)

            # Update the USER_SERVERS dictionary
            if discord_id not in USER_SERVERS:
                USER_SERVERS[discord_id] = []

            # Clear the current list and add the servers from the panel
            USER_SERVERS[discord_id] = [server['id'] for server in servers]
            print(f"Synced servers for user {discord_id}: {USER_SERVERS[discord_id]}")

            # Save the updated data to disk
            persistence.save_user_servers(USER_SERVERS)
            print(f"Saved updated user servers data to disk after syncing for user {discord_id}")

            return True
        except Exception as e:
            print(f"Exception syncing user servers: {str(e)}")
            traceback.print_exc()
            return False

    async def can_create_server(self, discord_id):
        """Check if a user can create more servers (limit of 2)"""
        try:
            # Sync the user's servers first
            await self.sync_user_servers(discord_id)

            if discord_id not in USER_SERVERS:
                USER_SERVERS[discord_id] = []
                return True

            return len(USER_SERVERS[discord_id]) < 2  # Max 2 servers per user
        except Exception as e:
            print(f"Exception checking if user can create server: {str(e)}")
            traceback.print_exc()
            # Default to allowing server creation if there's an error
            return True

    async def register_server_for_user(self, discord_id, server_id):
        """Register a server as belonging to a user"""
        if discord_id not in USER_SERVERS:
            USER_SERVERS[discord_id] = []

        USER_SERVERS[discord_id].append(server_id)

        # Save the updated data to disk
        persistence.save_user_servers(USER_SERVERS)
        print(f"Saved updated user servers data to disk after registering server {server_id} for user {discord_id}")

        return True

    async def reset_user_password(self, user_id):
        """Reset a user's password"""
        try:
            # First get the user details
            user_url = f"{self.base_url}/api/application/users/{user_id}"
            user_response = requests.get(user_url, headers=self.headers)

            if user_response.status_code != 200:
                print(f"Error getting user details: {user_response.text}")
                return None

            user_data = user_response.json()['attributes']

            # Generate a new random password
            new_password = secrets.token_urlsafe(12)

            # Update the user's password
            url = f"{self.base_url}/api/application/users/{user_id}"
            payload = {
                "email": user_data['email'],
                "username": user_data['username'],
                "first_name": user_data['first_name'],
                "last_name": user_data['last_name'],
                "password": new_password
            }

            response = requests.patch(url, headers=self.headers, json=payload)

            if response.status_code == 200:
                return new_password
            else:
                print(f"Error resetting password: {response.text}")
                return None
        except Exception as e:
            print(f"Exception resetting password: {str(e)}")
            traceback.print_exc()
            return None

    async def get_locations(self):
        """Get all available locations"""
        url = f"{self.base_url}/api/application/locations"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error getting locations: {response.text}")
            return []

    async def get_nodes(self):
        """Get all available nodes"""
        url = f"{self.base_url}/api/application/nodes"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error getting nodes: {response.text}")
            return []

    async def get_node_allocations(self, node_id):
        """Get all allocations for a node"""
        url = f"{self.base_url}/api/application/nodes/{node_id}/allocations"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()['data']
        else:
            print(f"Error getting allocations: {response.text}")
            return []

    async def get_available_allocation(self, node_id):
        """Get an available allocation for a node"""
        allocations = await self.get_node_allocations(node_id)
        available_allocations = []

        for allocation in allocations:
            if not allocation['attributes']['assigned']:
                available_allocations.append(allocation['attributes'])

        if available_allocations:
            return random.choice(available_allocations)
        else:
            return None

    async def find_available_node_and_allocation(self):
        """Find an available node and allocation"""
        nodes = await self.get_nodes()

        # Shuffle nodes to distribute servers evenly
        random.shuffle(nodes)

        for node in nodes:
            node_id = node['attributes']['id']
            allocation = await self.get_available_allocation(node_id)

            if allocation:
                return {
                    'node': node['attributes'],
                    'allocation': allocation
                }

        return None

    def get_allocation_sync(self, allocation_id):
        """Get allocation details by ID - sync version"""
        try:
            # First try to get the allocation from the nodes
            nodes_url = f"{self.base_url}/api/application/nodes"
            nodes_response = requests.get(nodes_url, headers=self.headers)

            if nodes_response.status_code == 200:
                nodes = nodes_response.json()['data']

                # Try each node
                for node in nodes:
                    node_id = node['attributes']['id']
                    allocations_url = f"{self.base_url}/api/application/nodes/{node_id}/allocations"
                    allocations_response = requests.get(allocations_url, headers=self.headers)

                    if allocations_response.status_code == 200:
                        allocations = allocations_response.json()['data']

                        # Look for the allocation
                        for allocation in allocations:
                            if allocation['attributes']['id'] == allocation_id:
                                return allocation['attributes']

            # If we couldn't find it, return a default allocation
            print(f"Could not find allocation {allocation_id}, returning default")
            return {
                'id': allocation_id,
                'ip': 'Unknown',
                'port': 'Unknown'
            }
        except Exception as e:
            print(f"Exception getting allocation: {str(e)}")
            traceback.print_exc()
            # Return a default allocation
            return {
                'id': allocation_id,
                'ip': 'Unknown',
                'port': 'Unknown'
            }
