"""Small helper for generating infrastructure snippets with a local LLM.

This file is intentionally separate from the production API. It is useful for a
portfolio demo where you want to show AI-assisted DevOps workflows without
making the runtime platform depend on a local Ollama installation.
"""

from __future__ import annotations

import subprocess


def generate_infra_snippet(prompt: str) -> str:
    command = ["ollama", "run", "llama3", prompt]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip()


if __name__ == "__main__":
    user_input = input("What infrastructure snippet should I generate? ")
    print(generate_infra_snippet(user_input))
