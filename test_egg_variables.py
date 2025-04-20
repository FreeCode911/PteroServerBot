import asyncio
from pterodactyl_api import PterodactylAPI

async def test_egg_variables():
    api = PterodactylAPI()
    
    # Test getting egg variables for a few different eggs
    nest_id = 5  # Use the nest ID from your config
    egg_ids = [16, 18, 22, 24]  # NodeJS, Python, UptimeKuma, Web Hosting
    
    for egg_id in egg_ids:
        print(f"\n--- Testing Egg ID: {egg_id} ---")
        
        # Get egg details
        egg_details = await api.get_egg_details(nest_id, egg_id)
        if egg_details:
            print(f"Egg Name: {egg_details.get('name')}")
            print(f"Docker Image: {egg_details.get('docker_image')}")
            print(f"Startup Command: {egg_details.get('startup')}")
            
            # Get variables from relationships
            variables = egg_details.get('relationships', {}).get('variables', {}).get('data', [])
            print(f"Found {len(variables)} variables in relationships")
            
            env_vars = {}
            for var_data in variables:
                var_attr = var_data.get('attributes', {})
                env_name = var_attr.get('env_variable')
                env_default = var_attr.get('default_value')
                env_required = var_attr.get('required', False)
                
                if env_name:
                    env_vars[env_name] = env_default or ''
                    print(f"  - {env_name}: {env_default} (Required: {env_required})")
            
            # Get variables using the API endpoint
            print("\nFetching variables using API endpoint:")
            api_variables = await api.get_egg_variables(nest_id, egg_id)
            print(f"Found {len(api_variables)} variables via API")
            
            for var in api_variables:
                var_attr = var.get('attributes', {})
                env_name = var_attr.get('env_variable')
                env_default = var_attr.get('default_value')
                env_required = var_attr.get('required', False)
                
                print(f"  - {env_name}: {env_default} (Required: {env_required})")
        else:
            print(f"Could not get details for egg {egg_id}")

if __name__ == "__main__":
    asyncio.run(test_egg_variables())
