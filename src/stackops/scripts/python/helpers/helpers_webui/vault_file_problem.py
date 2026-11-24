import json
import re
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_webui.vault_file_constants import VAULT_FIELD_WORDS, VAULT_SCHEMA_RULE_WORDS


# What is wrong with a vault file, for someone who has never seen its JSON. `where` names the login and secret by their place and label, `what`
# is a whole sentence, and `said` is the checker's own sentence with the file's path taken out. None of them ever holds a value: the checkers
# name places and fields, and the labels are read here from the file's names only. `line` and `column` are 0 unless the JSON itself is broken.
class VaultFileFinding(TypedDict):
    what: str
    where: str
    line: int
    column: int
    said: str


_JSON_PLACE = re.compile(r"line (\d+),? column (\d+)")
_ENTRY_PLACE = re.compile(r"""(?:\$\.)?entries\[(?P<login>\d+)\](?:\.secrets\[(?P<secret>\d+)\])?(?P<rest>(?:\.[A-Za-z]+|\[[^\]]*\])*)""")
_STEP = re.compile(r"""\.(?P<field>[A-Za-z]+)|\[(?P<item>\d+)\]|\[(?P<key>"(?:[^"\\]|\\.)*")\]""")
# The checkers' sentences by what they end in, each with the sentence shown for it. `{subject}` is the field or thing the checker points at,
# written to start a sentence, and `{place}` is the same thing written to stand inside one.
_SENTENCES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Secrets file not found"), "The file is not there."),
    (re.compile(r"must contain a JSON object"), "The file must hold one group of named fields, written in curly brackets."),
    (re.compile(r"must define an entries array"), "The file has no list of logins."),
    (re.compile(r"entries array must define at least one login"), "The file's list of logins is empty. A vault file holds at least one login."),
    (re.compile(r"contains unknown key\(s\): (?P<names>.+?)\.?$"), "{subject} has a field the vault does not know: {names}. Remove it, or correct its spelling."),
    (re.compile(r"expected at least one secret"), "This login has no secrets, and needs at least one."),
    (re.compile(r"rotateEveryDays must be an integer"), "{subject} must be a whole number of days, 1 or more."),
    (re.compile(r"must be a non-empty string"), "{subject} must be text, and cannot be empty."),
    (re.compile(r"must be an array of strings"), "{subject} must be a list of text items."),
    (re.compile(r"must be an object|expected object"), "{subject} must be a group of named fields, written in curly brackets."),
    (re.compile(r"expected array"), "{subject} must be a list, written in square brackets."),
    (re.compile(r"contains a non-string"), "There is an entry with no name in {place}."),
    (re.compile(r"must be a JSON value"), "{subject} holds something a JSON file cannot store."),
)
_SCHEMA_RULE = re.compile(r"failed schema rule '(?P<rule>[^']+)'")


def explain_vault_problem(message: str, path: Path) -> VaultFileFinding:
    said = message.replace(str(path), "the vault file")
    json_place = _JSON_PLACE.search(message)
    if json_place is not None and "Invalid JSON" in message:
        line, column = int(json_place.group(1)), int(json_place.group(2))
        return {"what": "The file is not written as valid JSON, so nothing in it can be read.", "where": f"""Line {line}, column {column}""", "line": line, "column": column, "said": said}
    place = _ENTRY_PLACE.search(message)
    subject = "The file" if place is None else _subject(rest=place.group("rest"), in_secret=place.group("secret") is not None)
    where = "" if place is None else _where(login=int(place.group("login")), secret=None if place.group("secret") is None else int(place.group("secret")), path=path)
    rule = _SCHEMA_RULE.search(message)
    place_words = f"""{subject[0].lower()}{subject[1:]}"""
    if rule is not None:
        sentence = VAULT_SCHEMA_RULE_WORDS.get(rule.group("rule"), f"""Something in {{place}} breaks the rule the schema calls {rule.group("rule")}.""")
        return {"what": sentence.format(place=place_words), "where": where, "line": 0, "column": 0, "said": said}
    for pattern, sentence in _SENTENCES:
        found = pattern.search(message)
        if found is not None:
            return {"what": sentence.format(subject=subject, place=place_words, **found.groupdict()), "where": where, "line": 0, "column": 0, "said": said}
    return {"what": said, "where": where, "line": 0, "column": 0, "said": said}


# The thing a checker points at inside a login or secret, as the start of a sentence: the last field it names, or an item or entry of that field.
def _subject(rest: str, in_secret: bool) -> str:
    steps = list(_STEP.finditer(rest))
    if len(steps) == 0:
        return "This secret" if in_secret else "This login"
    fields = [step.group("field") for step in steps if step.group("field") is not None]
    owner = VAULT_FIELD_WORDS.get(fields[-1], f"""its field {fields[-1]}""") if fields else "this entry"
    last = steps[-1]
    if last.group("item") is not None:
        return f"""Item {int(last.group("item")) + 1} of {owner}"""
    if last.group("key") is not None:
        return f"""The value named {json.loads(last.group("key"))}"""
    if len(fields) > 1 and fields[-2] == "metadata":
        return f"""The detail named {fields[-1]}"""
    return f"""{owner[0].upper()}{owner[1:]}"""


# Which login and secret, by their place in the file and the names found there. The file is read leniently: it is the one that failed its check.
def _where(login: int, secret: int | None, path: Path) -> str:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    entries = cast(dict[str, object], payload).get("entries") if isinstance(payload, dict) else None
    entry = cast(list[object], entries)[login] if isinstance(entries, list) and login < len(cast(list[object], entries)) else None
    fields = cast(dict[str, object], entry) if isinstance(entry, dict) else {}
    account = fields.get("accountName")
    text = f"""Login {login + 1}{_label(fields.get("name"))}{f" ({account})" if isinstance(account, str) and account.strip() else ""}"""
    if secret is None:
        return text
    secrets = fields.get("secrets")
    record = cast(list[object], secrets)[secret] if isinstance(secrets, list) and secret < len(cast(list[object], secrets)) else None
    return f"""{text} › secret {secret + 1}{_label(cast(dict[str, object], record).get("name") if isinstance(record, dict) else None)}"""


def _label(name: object) -> str:
    return f""", “{name}”""" if isinstance(name, str) and name.strip() else ""
