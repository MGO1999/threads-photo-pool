"""Extend the long-lived Threads token (valid 60 days) and report its expiry.

Fails the run if Meta returns a different token string, so you know to paste
the new one into the THREADS_ACCESS_TOKEN repository secret.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

token = os.environ.get("THREADS_ACCESS_TOKEN")
if not token:
    sys.exit("THREADS_ACCESS_TOKEN must be set")

query = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(f"https://graph.threads.net/refresh_access_token?{query}", timeout=60) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Refresh failed ({e.code}): {e.read().decode()}. Generate a new token in the Meta app.")

days = int(data.get("expires_in", 0)) // 86400
print(f"Token refreshed, valid for about {days} more days")
if data.get("access_token") and data["access_token"] != token:
    sys.exit("Meta issued a new token string. Generate one in the Meta app and update the secret.")
