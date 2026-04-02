#!/usr/bin/env python3
"""This script runs the main loop for the GTAW Admin Assistant program."""
import argparse

from detections.linehandler import main as run_line_handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the GTAW Admin Assistant watcher.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Enable test detection for lines containing 'testlog'.",
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

    print("GTAW Admin Assistant is running.")
    if args.test:
        print("Test mode enabled. Watching for lines containing 'testlog'.")
    if args.debug:
        print("Debug mode enabled. Printing watcher activity and new chat lines.")
    if args.replay_last > 0:
        print(f"Replaying the last {args.replay_last} parsed chat line(s) on startup.")

    try:
        run_line_handler(test_mode=args.test, debug=args.debug, replay_last=args.replay_last)
    except KeyboardInterrupt:
        print("Shutting down GTAW Admin Assistant.")
        return 0
    except Exception as error:
        print(f"GTAW Admin Assistant failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
