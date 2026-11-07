#!/usr/bin/env python3
"""Repeat the real installed-mode bridge request to catch shutdown races."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import subprocess
import sys

BRIDGE = Path(__file__).resolve().parents[1] / "crates/archon-distro/src/flatpak_bridge.py"
ITERATIONS = 200


def one_run(index):
    result = subprocess.run(
        [sys.executable, str(BRIDGE)],
        input='{"mode":"repositories"}\n',
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"bridge run {index} exited {result.returncode}: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    try:
        events = [json.loads(line) for line in result.stdout.splitlines()]
    except json.JSONDecodeError as error:
        raise AssertionError(f"bridge run {index} returned invalid output: {result.stdout!r}") from error
    if len(events) != 1 or events[0].get("event") != "result":
        raise AssertionError(f"bridge run {index} did not return one result event: {events!r}")


def main():
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(one_run, index) for index in range(ITERATIONS)]
        for future in as_completed(futures):
            future.result()
    print(f"PASS: {ITERATIONS} installed-mode bridge runs exited successfully")


if __name__ == "__main__":
    main()
