"""Publish due posts from queue/ to Threads.

Each file in queue/ is a JSON post:
{
  "publish_at": "2026-11-20T19:00:00+01:00",
  "theme": "Late light on whitewashed walls",
  "caption": "Short caption here",
  "images": ["photos/IMG_0001.jpg", "photos/IMG_0002.jpg"]
}

When a post is due, it is published (single image or carousel), recorded in
posted.json, and its queue file is moved to published/.
Needs env THREADS_ACCESS_TOKEN and GITHUB_REPOSITORY (set by GitHub Actions).
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://graph.threads.net/v1.0"
ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
PUBLISHED = ROOT / "published"
LOG = ROOT / "posted.json"


def call(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} failed: {e.code} {e.read().decode()}") from None


def image_url(repo, rel_path):
    return f"https://raw.githubusercontent.com/{repo}/main/{urllib.parse.quote(rel_path)}"


def wait_ready(container_id, token):
    for _ in range(30):
        status = call("GET", container_id, {"fields": "status,error_message", "access_token": token})
        if status.get("status") == "FINISHED":
            return
        if status.get("status") == "ERROR":
            raise RuntimeError(f"Container {container_id} failed: {status.get('error_message')}")
        time.sleep(10)
    raise RuntimeError(f"Container {container_id} not ready after 5 minutes")


def publish(post, token, repo):
    images = post["images"]
    caption = post.get("caption", "")
    if not 1 <= len(images) <= 10:
        raise ValueError("A post needs between 1 and 10 images")

    if len(images) == 1:
        container = call("POST", "me/threads", {
            "media_type": "IMAGE",
            "image_url": image_url(repo, images[0]),
            "text": caption,
            "access_token": token,
        })["id"]
    else:
        children = []
        for img in images:
            child = call("POST", "me/threads", {
                "media_type": "IMAGE",
                "image_url": image_url(repo, img),
                "is_carousel_item": "true",
                "access_token": token,
            })["id"]
            wait_ready(child, token)
            children.append(child)
        container = call("POST", "me/threads", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "text": caption,
            "access_token": token,
        })["id"]

    wait_ready(container, token)
    result = call("POST", "me/threads_publish", {"creation_id": container, "access_token": token})
    return result["id"]


def main():
    token = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip().strip("\"'")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        sys.exit("THREADS_ACCESS_TOKEN and GITHUB_REPOSITORY must be set")

    log = json.loads(LOG.read_text()) if LOG.exists() else []
    already = {img for entry in log for img in entry["images"]}
    now = datetime.now(timezone.utc)
    PUBLISHED.mkdir(exist_ok=True)
    failures = 0

    for f in sorted(QUEUE.glob("*.json")):
        post = json.loads(f.read_text())
        due = datetime.fromisoformat(post["publish_at"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due > now:
            continue

        repeats = [img for img in post["images"] if img in already]
        if repeats:
            print(f"Skipping {f.name}: already posted {repeats}")
            failures += 1
            continue

        try:
            post_id = publish(post, token, repo)
        except Exception as e:
            print(f"Failed {f.name}: {e}")
            failures += 1
            continue

        log.append({
            "file": f.name,
            "theme": post.get("theme", ""),
            "caption": post.get("caption", ""),
            "images": post["images"],
            "threads_id": post_id,
            "published_at": now.isoformat(),
        })
        already.update(post["images"])
        f.rename(PUBLISHED / f.name)
        LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")
        print(f"Published {f.name} as {post_id}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
