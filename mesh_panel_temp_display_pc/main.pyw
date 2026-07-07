#!/usr/bin/env python3
"""
Main entry point for Mesh Panel Temp Display (headless).
This file has a .pyw extension so Python launches it without a console window.
"""

import sys
import argparse

from mesh_panel_pc.app import AppController


def main():
    parser = argparse.ArgumentParser(description="Mesh Panel Temp Display")
    parser.add_argument("--minimized", action="store_true", help="Start minimized to system tray")
    args = parser.parse_args()

    app = AppController(start_minimized=args.minimized)
    app.run()


if __name__ == "__main__":
    main()
