import json
from pathlib import Path
from typing import Any


def load_json_file(filename: str) -> dict[str, Any]:
    """Load a JSON file from the prompts directory."""
    current_dir = Path(__file__).parent
    file_path = current_dir / filename

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# Load all prompt configurations
system_prompts = load_json_file('system_prompts.json')
user_prompts = load_json_file('user_prompts.json')
examples = load_json_file('examples.json')
