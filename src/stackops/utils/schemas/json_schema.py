import json
import re


def json_schema_document_text(*, content: str, schema_reference: str) -> str:
    tokens = [
        match
        for match in re.finditer(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/|[^\s]', content)
        if not match.group().startswith(("//", "/*"))
    ]
    if not tokens or tokens[0].group() != "{":
        return content

    schema_value = json.dumps(schema_reference, ensure_ascii=False)
    depth = 0
    expecting_key = False
    for index, token in enumerate(tokens):
        value = token.group()
        if value in {"{", "["}:
            depth += 1
            if depth == 1:
                expecting_key = True
        elif value in {"}", "]"}:
            depth -= 1
            if depth == 0:
                break
        elif depth == 1 and value == ",":
            expecting_key = True
        elif depth == 1 and expecting_key:
            expecting_key = False
            if not value.startswith('"'):
                continue
            try:
                key: object = json.loads(value)
            except json.JSONDecodeError:
                return content
            if key != "$schema":
                continue
            if index + 2 >= len(tokens) or tokens[index + 1].group() != ":":
                return content
            existing_value = tokens[index + 2]
            try:
                reference: object = json.loads(existing_value.group())
            except json.JSONDecodeError:
                return content
            if not isinstance(reference, str):
                return content
            return content[:existing_value.start()] + schema_value + content[existing_value.end():]

    insertion_point = tokens[0].end()
    separator = "," if len(tokens) > 1 and tokens[1].group() != "}" else ""
    newline = "\r\n" if "\r\n" in content else "\n"
    metadata = f"""{newline}  "$schema": {schema_value}{separator}"""
    return content[:insertion_point] + metadata + content[insertion_point:]
