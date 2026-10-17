"""One-time helper: run on YOUR computer to get the YouTube refresh token.

  pip install google-auth-oauthlib
  python uploader/get_token.py path/to/client_secret.json

A browser window opens: sign in with the Google account that owns the
Vangasirikam channel, pick the channel, and allow access. The script then
prints the three values to save as GitHub Actions secrets.
Never commit client_secret.json or the refresh token to the repo.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

if len(sys.argv) != 2:
    sys.exit("usage: python uploader/get_token.py client_secret.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
with open(sys.argv[1]) as f:
    info = json.load(f)
info = info.get("installed") or info.get("web")

print("\nSave these as GitHub Actions secrets (repo Settings > Secrets and variables > Actions):\n")
print(f"YT_CLIENT_ID     = {info['client_id']}")
print(f"YT_CLIENT_SECRET = {info['client_secret']}")
print(f"YT_REFRESH_TOKEN = {creds.refresh_token}")
