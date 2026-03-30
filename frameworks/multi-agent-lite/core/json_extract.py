from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    
    # Strategy 1: Look for markdown code blocks
    blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    for block in reversed(blocks):
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    # Strategy 2: Brace counting for all top-level JSON objects
    candidates = []
    start = text.find('{')
    while start >= 0:
        depth = 0
        in_string = False
        escape = False
        found_end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            else:
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        found_end = i
                        break
        
        if found_end != -1:
            candidate = text[start:found_end + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    candidates.append(parsed)
            except Exception:
                pass
            start = text.find('{', found_end + 1)
        else:
            break

    if candidates:
        return candidates[-1]

    return None
