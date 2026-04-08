#!/usr/bin/env python3
"""This script runs the main loop for the RAGE Player Assist program."""
import argparse

from config.app_config import APP_NAME, load_config
from detections.linehandler import main as run_line_handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"Run the {APP_NAME} watcher.")
    parser.add_argument(
        "--console",
        action="store_true",
        help="Run the watcher in console mode instead of the desktop GUI.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print watcher activity and every new parsed chat line.",
    )
    parser.add_argument(
        "--replay-last",
        type=int,
        default=0,
        help="Replay the last N parsed chat lines through the handler on startup.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.console:
            config = load_config()
            print(f"{APP_NAME} is running.")
            if args.debug:
                print("Debug mode enabled. Printing watcher activity and new chat lines.")
            if args.replay_last > 0:
                print(f"Replaying the last {args.replay_last} parsed chat line(s) on startup.")
            print(f"Using storage file: {config.storage_path}")

            run_line_handler(
                config=config,
                debug=args.debug,
                replay_last=args.replay_last,
            )
        else:
            from ui.qt_gui import launch as launch_gui

            launch_gui()
    except KeyboardInterrupt:
        print(f"Shutting down {APP_NAME}.")
        return 0
    except Exception as error:
        print(f"{APP_NAME} failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
