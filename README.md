# vangasirikalam-shorts

Shorts for the **Vangasirikam** YouTube channel, plus an automatic uploader.

- `videos/`: finished 1080x1920 MP4 Shorts
- `queue/`: one JSON file per video to upload (title, tags, publish time)
- `state/uploaded.json`: record of what has been uploaded (written by the workflow)
- `uploader/`: upload script and one-time token helper
- `.github/workflows/upload.yml`: runs every hour and uploads any video whose `publishAt` time has passed (max 3 per run)

## One-time setup (about 30 minutes)

### 1. Google Cloud project
1. Go to https://console.cloud.google.com and create a project (e.g. `vangasirikam-uploader`).
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **APIs & Services → OAuth consent screen**: User type **External**; app name `Vangasirikam Uploader`; add your email; add scope `.../auth/youtube.upload`; add the channel's Google account as a **Test user**; then click **Publish app** (set it to *In production*). In *Testing* mode, refresh tokens expire after 7 days.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** → type **Desktop app** → download the JSON (`client_secret_....json`). Keep it private and don't commit it.

### 2. Get the refresh token (on your computer)
```bash
git clone https://github.com/vangasirikalam/vangasirikalam-shorts
cd vangasirikalam-shorts
pip install google-auth-oauthlib
python uploader/get_token.py ~/Downloads/client_secret_XXXX.json
```
Sign in with the account that owns the channel, choose the **Vangasirikam** channel, and allow access. It prints three values.

### 3. Add GitHub secrets
Repo **Settings → Secrets and variables → Actions → New repository secret**:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

### 4. Test
**Actions → Upload due Shorts to YouTube → Run workflow** (tick *Dry run* first, then run for real).

### 5. Apply for the API audit (needed for public uploads)
YouTube locks videos uploaded by **unaudited** API projects to **private**. Apply via the
[YouTube API Services audit form](https://support.google.com/youtube/contact/yt_api_form).
Until it's approved, keep using Metricool for public posts.

## Limits
- Default quota: 10,000 units/day; each upload costs ~1,600 units, so about **6 uploads/day**.
- New channels also have a YouTube daily upload cap; verify the channel at https://youtube.com/verify.

## Queue file example (`queue/2026-10-20_1800_robot_dominoes.json`)
```json
{
  "file": "videos/short4_robot_dominoes.mp4",
  "title": "Robot vs 100 Dominoes 😂 #Shorts",
  "description": "Wait for the last one... #Shorts #satisfying #toys",
  "tags": ["shorts", "satisfying", "dominoes", "robot", "toys"],
  "category": "24",
  "madeForKids": true,
  "privacy": "public",
  "publishAt": "2026-10-20T18:00:00+05:30"
}
```
