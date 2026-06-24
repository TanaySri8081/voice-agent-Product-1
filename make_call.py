import os
import sys

# Add backend directory to sys path so we can resolve imports correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.make_call import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
