"""Check that the stored Threads token still works (it lasts 60 days)."""

import json
import os
import sys
import urllib.parse
import urllib.request

token = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip().strip("\"'")
if not token:
    sys.exit("THREADS_ACCESS_TOKEN must be set")

query = urllib.parse.urlencode({"fields": "id,username", "access_token": token})
try:
    with urllib.request.urlopen(f"https://graph.threads.net/v1.0/me?{query}", timeout=60) as r:
        me = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Token check failed ({e.code}): {e.read().decode()}. Generate a new token in the Meta app.")

print(f"Token OK for @{me.get('username')}")
