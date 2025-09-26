#!/usr/bin/env python3
"""
System Updater Script
Runs various system update commands concurrently and generates a summary using Gemini API.
"""

import subprocess
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import concurrent.futures
import threading
import time
from typing import Tuple, Dict


# Thread-safe printing
print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    """Thread-safe print function."""
    with print_lock:
        print(*args, **kwargs)


def run_command(cmd: str, description: str) -> Tuple[bool, str, str]:
    """Run a command and capture its output. Returns (success, output, description)."""
    safe_print(f"🚀 Starting: {description}")
    start_time = time.time()

    try:
        # Use login shell to ensure all aliases and functions are loaded
        # First try to source common shell configs, then run the command
        full_cmd = f"""
source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null || true
{cmd}
"""
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            executable="/bin/zsh",  # Use zsh explicitly
        )
        output = f"{result.stdout}\n{result.stderr}".strip()

        elapsed = time.time() - start_time

        if result.returncode == 0:
            safe_print(f"✅ Completed: {description} ({elapsed:.1f}s)")
        else:
            safe_print(f"⚠️  Completed with warnings: {description} ({elapsed:.1f}s)")

        return result.returncode == 0, output, description
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        error_msg = f"❌ {description} timed out after {elapsed:.1f}s"
        safe_print(error_msg)
        return False, error_msg, description

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"❌ {description} failed after {elapsed:.1f}s: {str(e)}"
        safe_print(error_msg)
        return False, error_msg, description


def run_all_updates() -> str:
    """Run all system update commands concurrently and return combined output."""

    update_commands = [
        (
            "brew update && brew upgrade && brew cleanup && brew doctor || true",
            "Updating Homebrew",
        ),
        ("nvm upgrade", "Updating NVM"),
        ("pnpm up -g --latest", "Updating PNPM"),
        ("claude update", "Updating Claude"),
        ("deno upgrade", "Updating Deno"),
        ("omz update", "Updating Oh My Zsh"),
    ]

    print(f"🏁 Starting {len(update_commands)} updates concurrently...")
    print("=" * 60)

    # Store results indexed by description for consistent ordering
    results: Dict[str, Tuple[bool, str]] = {}
    start_time = time.time()

    # Run all commands concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # Submit all tasks
        future_to_cmd = {
            executor.submit(run_command, cmd, desc): desc
            for cmd, desc in update_commands
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_cmd):
            try:
                success, output, description = future.result()
                results[description] = (success, output)
            except Exception as e:
                description = future_to_cmd[future]
                results[description] = (False, f"Exception: {str(e)}")

    total_time = time.time() - start_time
    print("=" * 60)
    print(f"🎯 All updates completed in {total_time:.1f}s")

    # Build output in original order
    all_output = []
    all_output.append("SYSTEM UPDATE REPORT")
    all_output.append("=" * 50)
    all_output.append(f"Total execution time: {total_time:.1f} seconds")
    all_output.append("")

    for cmd, description in update_commands:
        if description in results:
            success, output = results[description]
            all_output.append(f"{description}:")
            all_output.append("-" * len(description))
            all_output.append(output if output else "No output")

            if not success:
                all_output.append("⚠️ Command failed or had issues")

            all_output.append("")  # Empty line separator

    return "\n".join(all_output)


def generate_summary(update_output: str) -> str:
    """Generate a summary using Gemini API."""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "❌ Error: GEMINI_API_KEY environment variable is not set"

    print("========== Generating Summary ==========")
    print("📡 Calling Gemini API for summary...")

    try:
        # Prepare the payload
        prompt = f"Summarize the following system update commands result in a bullet list format:\n\n{update_output}"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {},
        }

        # Make API call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        # Prepare request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        # Make the request
        response = urllib.request.urlopen(req, timeout=30)

        if response.status == 200:
            response_data = json.loads(response.read().decode("utf-8"))
            summary = (
                response_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "No summary generated")
            )
            print("✅ Summary generated successfully")
            return f"📋 SUMMARY:\n{'-' * 20}\n{summary}"
        else:
            error_msg = f"❌ API call failed with HTTP {response.status}"
            print(error_msg)
            return error_msg

    except urllib.error.URLError as e:
        error_msg = f"❌ Network error: {str(e)}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


def main():
    """Main function."""
    print("🚀 Starting Concurrent System Updates...")
    print("=" * 50)

    # Run all updates concurrently
    update_output = run_all_updates()

    # Print the full output
    print("\n" + "=" * 50)
    print("FULL UPDATE OUTPUT:")
    print("=" * 50)
    print(update_output)

    # Generate and print summary
    print("\n" + "=" * 50)
    summary = generate_summary(update_output)
    print(summary)

    print("\n🎉 Concurrent system update process completed!")


if __name__ == "__main__":
    main()
