import asyncio
from pterodactyl_api import PterodactylAPI
from config import SERVER_TEMPLATES

async def test_web_hosting():
    api = PterodactylAPI()
    
    # Print the web-hosting template configuration
    web_hosting = SERVER_TEMPLATES.get('web-hosting', {})
    print(f"Web Hosting Template Configuration:")
    print(f"  Name: {web_hosting.get('name')}")
    print(f"  Description: {web_hosting.get('description')}")
    print(f"  Memory: {web_hosting.get('memory')} MB")
    print(f"  Disk: {web_hosting.get('disk')} MB")
    print(f"  CPU: {web_hosting.get('cpu')}")
    print(f"  Nest ID: {web_hosting.get('nest')}")
    print(f"  Egg ID: {web_hosting.get('egg')}")
    print(f"  Environment Variables: {web_hosting.get('env', {})}")
    
    # Get egg details
    nest_id = web_hosting.get('nest')
    egg_id = web_hosting.get('egg')
    
    if nest_id and egg_id:
        egg_details = await api.get_egg_details(nest_id, egg_id)
        if egg_details:
            print(f"\nEgg Details:")
            print(f"  Name: {egg_details.get('name')}")
            print(f"  Docker Image: {egg_details.get('docker_image')}")
            
            # Get environment variables
            env_vars = {}
            egg_variables = egg_details.get('relationships', {}).get('variables', {}).get('data', [])
            if egg_variables:
                print(f"\nFound {len(egg_variables)} variables for egg {egg_id}:")
                
                for var_data in egg_variables:
                    var_attr = var_data.get('attributes', {})
                    env_name = var_attr.get('env_variable')
                    env_default = var_attr.get('default_value')
                    env_required = var_attr.get('required', False)
                    
                    print(f"  - {env_name}: {env_default} (Required: {env_required})")
                    
                    if env_name:
                        env_vars[env_name] = env_default or ''
            
            # Apply template-specific environment variables
            if 'env' in web_hosting:
                print(f"\nApplying template-specific environment variables:")
                for key, value in web_hosting['env'].items():
                    env_vars[key] = value
                    print(f"  - {key}: {value}")
            
            print(f"\nFinal environment variables that would be used:")
            for key, value in env_vars.items():
                print(f"  - {key}: {value}")
        else:
            print(f"Could not get details for egg {egg_id} in nest {nest_id}")
    else:
        print("Nest ID or Egg ID not specified in the web-hosting template")

if __name__ == "__main__":
    asyncio.run(test_web_hosting())
