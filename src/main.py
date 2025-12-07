import asyncio

from dotenv import load_dotenv

from src.cli import main as cli_main

load_dotenv()


if __name__ == "__main__":
    asyncio.run(cli_main())
