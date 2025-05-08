import os
import sys
import uvicorn
import argparse
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description="Run uvicorn server with environment variable configuration")
    parser.add_argument('--env-file', type=str, help='Path to .env file to load')
    args = parser.parse_args()

    # Load environment variables from file if specified
    if args.env_file and os.path.exists(args.env_file):
        load_dotenv(args.env_file)

    # Get configuration from environment variables
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    app_module = os.getenv('APP_MODULE', 'aggregator_server:app')
    reload = os.getenv('RELOAD', 'False').lower() == 'true'

    print(f"Starting server with {app_module} on {host}:{port} (reload={reload})")

    # Start the uvicorn server
    uvicorn.run(
        app_module,
        host=host,
        port=port,
        reload=reload
    )


if __name__ == "__main__":
    main()