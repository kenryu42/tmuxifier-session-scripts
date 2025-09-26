#!/usr/bin/env python3
"""
System Updater Script
Runs various system update commands and generates a summary using Gemini API.
"""

import subprocess
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from typing import Tuple


def run_command(cmd: str, description: str) -> Tuple[bool, str]:
    """Run a command and capture its output."""
    print(f"========== {description} ==========")
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

        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
        else:
            print(f"⚠️  {description} completed with warnings/errors")

        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        error_msg = f"❌ {description} timed out after 5 minutes"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"❌ {description} failed: {str(e)}"
        print(error_msg)
        return False, error_msg


def run_all_updates() -> str:
    """Run all system update commands and return combined output."""

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

    all_output = []
    all_output.append("SYSTEM UPDATE REPORT")
    all_output.append("=" * 50)

    for cmd, description in update_commands:
        success, output = run_command(cmd, description)
        all_output.append(f"\n{description}:")
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
    print("🚀 Starting System Updates...")
    print("=" * 50)

    # Run all updates
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

    print("\n🎉 System update process completed!")


if __name__ == "__main__":
    main()
