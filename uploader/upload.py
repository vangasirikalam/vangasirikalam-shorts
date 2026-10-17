"""Upload due Shorts from queue/ to YouTube via the YouTube Data API v3.

Each queue/*.json manifest describes one video:
{
  "file": "videos/short4_example.mp4",
  "title": "Title up to 100 chars #Shorts",
  "description": "Text shown under the video",
  "tags": ["shorts", "satisfying"],
  "category": "24",                # 24 = Entertainment
  "madeForKids": true,
  "privacy": "public",             # public | unlisted | private
  "publishAt": "2026-10-20T18:00:00+05:30"
}

A manifest is "due" when publishAt <= now. Uploaded manifests are recorded in
state/uploaded.json so they are never uploaded twice.

Env vars (GitHub Actions secrets): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Flags: --dry-run (no API calls), --max N (default 3 uploads per run).
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "queue")
STATE = os.path.join(ROOT, "state", "uploaded.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REQUIRED = ["file", "title", "publishAt"]


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def due_manifests(state, now):
    out = []
    for path in sorted(glob.glob(os.path.join(QUEUE, "*.json"))):
        name = os.path.basename(path)
        if name in state:
            continue
        with open(path) as f:
            m = json.load(f)
        missing = [k for k in REQUIRED if k not in m]
        if missing:
            print(f"SKIP {name}: missing {missing}")
            continue
        when = dt.datetime.fromisoformat(m["publishAt"])
        if when.tzinfo is None:
            print(f"SKIP {name}: publishAt needs a timezone offset, e.g. +05:30")
            continue
        if when > now:
            continue
        video = os.path.join(ROOT, m["file"])
        if not os.path.exists(video):
            print(f"SKIP {name}: video file not found: {m['file']}")
            continue
        if len(m["title"]) > 100:
            print(f"SKIP {name}: title longer than 100 characters")
            continue
        out.append((when, name, m, video))
    out.sort()
    return out


def youtube_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(yt, m, video):
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": m["title"],
            "description": m.get("description", ""),
            "tags": m.get("tags", []),
            "categoryId": str(m.get("category", "24")),
        },
        "status": {
            "privacyStatus": m.get("privacy", "public"),
            "selfDeclaredMadeForKids": bool(m.get("madeForKids", True)),
            "containsSyntheticMedia": False,
        },
    }
    media = MediaFileUpload(video, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    tries = 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except Exception as e:  # retry transient errors a few times
            tries += 1
            if tries > 4 or "quotaExceeded" in str(e) or "uploadLimitExceeded" in str(e):
                raise
            time.sleep(2 ** tries)
    return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    state = load_state()
    due = due_manifests(state, now)
    print(f"{len(due)} video(s) due at {now.isoformat(timespec='minutes')}")
    if not due:
        return 0

    yt = None if args.dry_run else youtube_client()
    failed = 0
    for when, name, m, video in due[: args.max]:
        if args.dry_run:
            print(f"DRY-RUN would upload {name}: {m['title']} ({m.get('privacy', 'public')})")
            continue
        try:
            resp = upload(yt, m, video)
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {e}")
            if "quotaExceeded" in str(e) or "uploadLimitExceeded" in str(e):
                print("Daily limit reached; remaining videos will go in the next run.")
                break
            continue
        status = resp.get("status", {})
        state[name] = {
            "videoId": resp["id"],
            "url": f"https://youtube.com/shorts/{resp['id']}",
            "uploadedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "privacy": status.get("privacyStatus"),
        }
        save_state(state)
        print(f"OK {name}: {state[name]['url']} ({status.get('privacyStatus')})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
