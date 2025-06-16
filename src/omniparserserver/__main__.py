#!/usr/bin/env python3
"""
Main entry point for the OmniParser server
"""

import asyncio
import logging
from omniparserserver.server import serve

def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())

if __name__ == "__main__":
    main()
