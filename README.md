# threads-photo-pool

A pool of photos plus a scheduler that posts them to Threads.

## How it works

- `photos/` holds the image pool (JPEG, under 8 MB each).
- `photos/catalog.json` describes each image (subject, place, light, colour) so themed posts can be built.
- `queue/` holds posts waiting to go out, one JSON file per post.
- A GitHub Action runs every hour, publishes any post whose time has come, logs it in `posted.json` and moves it to `published/`.
- An image already in `posted.json` is never posted again.

## Queue file format

```json
{
  "publish_at": "2026-11-20T19:00:00+01:00",
  "theme": "Late light on whitewashed walls",
  "caption": "Short caption",
  "images": ["photos/IMG_0001.jpg", "photos/IMG_0002.jpg"]
}
```

One image makes a single post. Two to ten images make a carousel.

## Setup

1. Add the Threads token as a repository secret named `THREADS_ACCESS_TOKEN`
   (Settings, Secrets and variables, Actions).
2. Run "Publish due posts" once from the Actions tab to test.

The token lasts 60 days. "Check Threads token" tests it every Monday and fails
(GitHub emails you) once it stops working. Then generate a new one in the Meta
app and update the secret.
