#!/usr/bin/env python3
"""Import Logseq CRM contacts into PingCRM."""
import csv
import re
import subprocess
import json

API = "http://localhost:3001/api"

# --- 1. Parse Logseq contacts ---

CONTACTS = [
    {
        "handle": "@lkar",
        "name": "Леонид Карпенко",
        "role": "#ceo",
        "met": "[[@rotek]], совместный проект [[phoenix]]",
        "birthday": "03.07",
    },
    {
        "handle": "@fgur",
        "name": "Федя",
        "role": "",
        "met": "",
        "birthday": "",
    },
    {
        "handle": "@nvoi",
        "name": "Никита Войтенко",
        "role": "",
        "met": "[[@bmstu]]",
        "birthday": "",
    },
    {
        "handle": "@vzdo",
        "name": "Влад Здоренко",
        "role": "",
        "met": "[[@bmstu]]",
        "birthday": "",
    },
    {
        "handle": "@keyten",
        "name": "Дмитрий",
        "role": "",
        "met": "[[@vas3k]]",
        "birthday": "",
    },
    {
        "handle": "@dmel",
        "name": "Дима Мельников",
        "role": "manager",
        "met": "[[@haier]]",
        "birthday": "",
    },
]


def clean_logseq(text: str) -> str:
    """Strip [[ ]] links, leading #, extra whitespace."""
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)  # [[link]] -> link
    text = text.strip().lstrip("#").strip()
    return text


def birthday_to_mm_dd(raw: str) -> str:
    """Convert DD.MM to MM-DD."""
    raw = raw.strip()
    if not raw:
        return ""
    parts = raw.split(".")
    if len(parts) == 2:
        return f"{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return raw


# --- 2. Build CSV ---

csv_path = "/tmp/logseq_contacts.csv"
rows = []
for c in CONTACTS:
    notes_parts = []
    met = clean_logseq(c["met"])
    if met:
        notes_parts.append(f"Met: {met}")
    notes_parts.append(f"Logseq handle: {c['handle']}")
    notes = "; ".join(notes_parts)

    role = clean_logseq(c["role"])
    birthday = birthday_to_mm_dd(c["birthday"])

    rows.append({
        "name": c["name"],
        "title": role,
        "notes": notes,
        "tags": f"logseq; {c['handle']}",
        "birthday": birthday,
    })

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "title", "notes", "tags", "birthday"])
    writer.writeheader()
    writer.writerows(rows)

print(f"CSV written: {csv_path}")
for r in rows:
    print(f"  {r}")

# --- 3. Register user ---

def curl(method, path, data=None, files=None, token=None, form=None):
    cmd = ["curl", "-s", "-X", method, f"{API}{path}"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    if form:
        for k, v in form.items():
            cmd += ["-d", f"{k}={v}"]
    if files:
        for k, v in files.items():
            cmd += ["-F", f"{k}=@{v}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout.strip() else {}


# Register
reg = curl("POST", "/v1/auth/register", data={
    "email": "evgeny@pingcrm.dev",
    "password": "changeme123",
    "full_name": "Evgeny Kim",
})
print(f"\nRegister: {json.dumps(reg, ensure_ascii=False)}")

# Login
login = curl("POST", "/v1/auth/login", form={
    "username": "evgeny@pingcrm.dev",
    "password": "changeme123",
})
print(f"Login: {json.dumps(login, ensure_ascii=False)}")
token = login.get("data", {}).get("access_token", "")
if not token:
    print("ERROR: No token. Aborting.")
    exit(1)

# Import CSV
imp = curl("POST", "/v1/contacts/import/csv", files={"file": csv_path}, token=token)
print(f"\nImport: {json.dumps(imp, ensure_ascii=False)}")
