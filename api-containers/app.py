import os
import sys
import argparse
import uvicorn
from dotenv import load_dotenv

# Add edgefl directory to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGEFL_PATH = os.path.join(PROJECT_ROOT, "edgefl")
sys.path.append(EDGEFL_PATH)

def main():
    parser = argparse.ArgumentParser(description="Run server based on environment variables")
    parser.add_argument('--env-file', type=str, help='Path to .env file to load')
    parser.add_argument('--port', type=int, help='Override port from env file')
    args = parser.parse_args()

    # Load environment variables from file if specified
    if args.env_file and os.path.exists(args.env_file):
        load_dotenv(args.env_file)
    else:
        load_dotenv()  # Load from default .env if it exists

    # Determine which server to run based on SERVER_TYPE
    server_type = os.getenv('SERVER_TYPE', '').lower()

    if not server_type:
        print("ERROR: SERVER_TYPE environment variable not set. Set to 'aggregator' or 'node'")
        sys.exit(1)

    # Get port from args, env var, or default
    port = args.port if args.port else int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    reload = os.getenv('RELOAD', 'False').lower() == 'true'

    print(f"Starting {server_type} server on {host}:{port}")

    if server_type == 'aggregator':
        app_module = "platform_components.aggregator.aggregator_server:app"
        uvicorn.run(app_module, host=host, port=port, reload=reload)

    elif server_type == 'node':
        app_module = "platform_components.node.node_server:app"
        uvicorn.run(app_module, host=host, port=port, reload=reload)

    else:
        print(f"ERROR: Invalid SERVER_TYPE '{server_type}'. Must be 'aggregator' or 'node'")
        sys.exit(1)


if __name__ == "__main__":
    main()