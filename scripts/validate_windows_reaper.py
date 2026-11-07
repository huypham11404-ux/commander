"""Deterministic verification script for running on physical Windows 10/11 workstation with REAPER.
Usage:
    python scripts/validate_windows_reaper.py --ipc-dir "%TEMP%\\reaper_mcp"
"""
import sys
import os
import time
import argparse
from commander.driver.reaper_driver import ReaperFileDriver
from commander.protocol.schema import CommandRequest

def main():
    parser = argparse.ArgumentParser(description="Validate live REAPER connection on Windows")
    parser.add_argument("--ipc-dir", default=None, help="Path to REAPER IPC directory")
    args = parser.parse_args()

    print(f"[*] Initializing ReaperFileDriver on platform '{sys.platform}'...")
    driver = ReaperFileDriver(ipc_dir=args.ipc_dir)

    print(f"[*] Checking for REAPER heartbeat lock file at: {driver.lock_file}")
    if not driver.is_alive():
        print("[!] ERROR: REAPER is not responding or reaper_mcp_server.lua is not running.")
        print("    Please load and run reaper_mcp_server.lua in REAPER Actions.")
        sys.exit(1)

    print("[+] REAPER heartbeat verified alive.")

    # 1. Project state check
    print("[*] Sending 'project_get_state' command...")
    t0 = time.perf_counter()
    state = driver.get_project_state()
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"[+] Success in {dt:.2f}ms. Project state: {state}")

    # 2. Track creation check
    print("[*] Sending 'track_create' command for test track...")
    req = CommandRequest(command="track_create", params={"name": "Commander_Live_Test_Track"})
    resp = driver.send_command(req, timeout=5.0)
    if resp.status == "ok":
        print(f"[+] Track created successfully: {resp.result}")
    else:
        print(f"[!] Track creation failed: {resp.error}")
        sys.exit(2)

    print("[***] PHYSICAL WINDOWS REAPER VERIFICATION COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    main()
