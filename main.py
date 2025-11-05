#!/usr/bin/env python3
"""
Seal - PNCP Lacre (Security Seals) Tender Discovery System
Main entry point for the application

This is a wrapper that delegates to the lacre-specific implementation in src/lacre/.
"""

if __name__ == "__main__":
    import sys
    import os
    import asyncio

    # Add src directory to Python path for imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

    from src.lacre.main_lacre import main
    asyncio.run(main())
