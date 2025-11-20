#!/usr/bin/env python3
"""
System Updater Script
Runs various system update commands concurrently with a rich UI and AI summary.
"""

import subprocess
import json
import os
import urllib.request
import concurrent.futures
import time
import signal
import sys
from typing import Tuple, Dict
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel

# Configuration
MODEL = "gemini-2.0-flash-lite"
MAX_WORKERS = 6
TIMEOUT_SECONDS = 300

# Command Definitions
# shell_source: True if the command relies on shell aliases/functions (nvm, omz)
# shell_source: False for standard binaries (brew, pnpm, etc.) to save startup time
UPDATE_COMMANDS = [
    {
        "cmd": "brew update && brew upgrade && brew cleanup && brew doctor || true",
        "desc": "Updating Homebrew",
        "shell_source": False
    },
    {
        "cmd": "nvm upgrade",  # Assumes user alias or extension
        "desc": "Updating NVM",
        "shell_source": True
    },
    {
        "cmd": "pnpm up -g --latest",
        "desc": "Updating PNPM",
        "shell_source": False
    },
    {
        "cmd": "claude update",
        "desc": "Updating Claude",
        "shell_source": False
    },
    {
        "cmd": "omz update",
        "desc": "Updating Oh My Zsh",
        "shell_source": True
    },
]

console = Console()


def get_enhanced_env() -> Dict[str, str]:
    """Returns environment variables with common bin paths added."""
    env = os.environ.copy()
    common_paths = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/bin"),
    ]
    current_path = env.get("PATH", "")

    # Prepend common paths if not present
    new_paths = [p for p in common_paths if p not in current_path]
    if new_paths:
        env["PATH"] = ":".join(new_paths) + ":" + current_path

    return env


def run_command(cmd_config: Dict) -> Tuple[bool, str, str]:
    """Run a single update command."""
    cmd = cmd_config["cmd"]
    desc = cmd_config["desc"]
    needs_shell = cmd_config.get("shell_source", True)

    try:
        if needs_shell:
            # Use login shell to ensure all aliases and functions are loaded
            full_cmd = f"""
source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null || true
{cmd}
"""
            # For shell sourcing, we need the exact executable
            shell_exec = os.environ.get("SHELL", "/bin/zsh")
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                executable=shell_exec,
            )
        else:
            # Run directly with enhanced PATH for speed
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                env=get_enhanced_env(),
            )

        output = f"{result.stdout}\n{result.stderr}".strip()
        success = result.returncode == 0

        return success, output, desc

    except subprocess.TimeoutExpired:
        return False, f"❌ Timed out after {TIMEOUT_SECONDS}s", desc
    except Exception as e:
        return False, f"❌ Execution failed: {str(e)}", desc


def run_all_updates() -> str:
    """Run updates with a progress bar."""
    results: Dict[str, Tuple[bool, str]] = {}
    start_time = time.time()

    # Create a rich progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.fields[status]}"),
        console=console,
        expand=True,
    ) as progress:

        # Create a main task
        overall_task = progress.add_task(
            "[green]Overall Progress", total=len(UPDATE_COMMANDS), status="Starting..."
        )

        # Map futures to command descriptions
        futures = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for config in UPDATE_COMMANDS:
                future = executor.submit(run_command, config)
                futures[future] = config["desc"]

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures):
                desc = futures[future]
                try:
                    success, output, _ = future.result()
                    results[desc] = (success, output)

                    status_icon = "✅" if success else "❌"
                    progress.console.print(f"{status_icon} Finished: [bold]{desc}[/bold]")

                except Exception as e:
                    results[desc] = (False, f"Exception: {str(e)}")
                    progress.console.print(f"❌ Error: [bold]{desc}[/bold] - {e}")

                progress.advance(overall_task)
                progress.update(overall_task, status=f"Completed {desc}")

    total_time = time.time() - start_time

    # Build report
    report_lines = [
        "SYSTEM UPDATE REPORT",
        "=" * 60,
        f"Total execution time: {total_time:.1f} seconds",
        "",
    ]

    for config in UPDATE_COMMANDS:
        desc = config["desc"]
        if desc in results:
            success, output = results[desc]
            icon = "✅" if success else "❌"
            report_lines.append(f"{icon} {desc}:")
            report_lines.append("-" * len(desc))
            report_lines.append(output if output.strip() else "(No output)")
            if not success:
                report_lines.append("⚠️ Command failed")
            report_lines.append("")

    return "\n".join(report_lines)


def generate_summary(update_output: str) -> str:
    """Generate a summary using Gemini API with an improved prompt."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "❌ Error: GEMINI_API_KEY environment variable is not set"

    console.print(Panel("📡 Generating AI Summary...", style="blue"))

    prompt = (
        "Analyze the following system update logs and provide a concise summary markdown.\n"
        "Structure the response as:\n"
        "1. **Summary**: 1-sentence overview (e.g., 'All updates successful' or 'Homebrew failed').\n"
        "2. **Changes**: Bullet points of installed/upgraded packages (extract version numbers if possible).\n"
        "3. **Errors**: (Only if any) Bullet points of what failed and why.\n"
        "Ignore routine 'cleaning up' or 'already up to date' messages unless relevant.\n\n"
        f"Logs:\n{update_output}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent"
        f"?key={api_key}"
    )
    data = json.dumps(payload).encode("utf-8")

    last_error = "Unknown error"
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    response_data = json.loads(response.read().decode("utf-8"))
                    return (
                        response_data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "No summary generated")
                    )
        except Exception as e:
            last_error = str(e)
            time.sleep(1)

    return f"❌ Failed to generate summary: {last_error}"


def signal_handler(sig, frame):
    console.print("\n[bold red]⚠️  Interrupted by user. Exiting...[/bold red]")
    sys.exit(1)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    console.print(Panel.fit("🚀 [bold]System Updater[/bold] initialized", style="bold green"))

    update_output = run_all_updates()

    summary = generate_summary(update_output)

    console.print("\n")
    if not summary.startswith("❌"):
        console.print(Markdown(summary))
    else:
        console.print(summary)
        # Fallback to raw output if AI fails
        console.print(Panel(update_output, title="Raw Output", expand=False))

    console.print("\n[bold green]✨ All tasks completed![/bold green]")


if __name__ == "__main__":
    main()
