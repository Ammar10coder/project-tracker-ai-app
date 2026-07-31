# Project Tracker AI — standalone app (no Docker)

This is your bot repackaged as a real desktop app. No Docker, no terminal,
no Python install needed on the machine that runs it. You start/stop it by
clicking a button in your browser.

## 1. One-time setup: get the app built for Windows and Mac

1. Create a new **private** repository on GitHub (e.g. `project-tracker-ai-app`).
2. Push everything in this folder to it:
   ```
   cd project_tracker_ai_app
   git init
   git add .
   git commit -m "Standalone app"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
3. On GitHub, open the **Actions** tab. A workflow called
   "Build Project Tracker AI" runs automatically (takes ~3-5 minutes).
4. When it finishes (green check), click into the run → scroll to
   **Artifacts** → download:
   - `ProjectTrackerAI-windows.zip` for Windows PCs
   - `ProjectTrackerAI-mac.zip` for Mac

Every time you push a change to `main`, it rebuilds both automatically —
you never have to touch PyInstaller, Docker, or run a build command
yourself.

## 2. Running it on Windows

1. Unzip `ProjectTrackerAI-windows.zip` anywhere (Desktop, Documents — not
   inside "Program Files").
2. Double-click `ProjectTrackerAI.exe` inside the extracted folder.
3. Windows may show a SmartScreen warning ("Windows protected your PC")
   because the exe isn't code-signed — click **More info → Run anyway**.
   This is normal for an app built outside the Microsoft Store.
4. Your browser opens automatically to the dashboard.

## 3. Running it on Mac

1. Unzip `ProjectTrackerAI-mac.zip` anywhere.
2. Double-click **"Launch ProjectTrackerAI.command"** inside the extracted
   folder (not the plain `ProjectTrackerAI` file).
3. macOS will block it the first time ("cannot be opened because the
   developer cannot be verified"). Go to **System Settings → Privacy &
   Security**, scroll down, and click **Open Anyway** next to the blocked
   app message. Then run it again — this is only needed once.
4. Your browser opens automatically to the dashboard.

## 4. First-time configuration (do this once per machine)

In the dashboard, go to the **Settings** tab and fill in:

- **Telegram**: API ID / API Hash (from https://my.telegram.org →
  API Development Tools), your phone number, and the exact group chat name
  to listen in.
- **AI keys**: at minimum a **Gemini API key**. Groq and OpenRouter keys
  are optional automatic fallbacks.
- **Email**: your Gmail address and a Gmail **App Password** (Google
  Account → Security → 2-Step Verification → App passwords — this is a
  16-character code, not your normal password).
- **Google Drive**: click **Connect Google Drive** once — it opens your
  browser to sign in with Google. Only needs doing once per machine.

Click **Save settings**, then go back to the **Dashboard** tab and click
**Start bot**.

## 5. Telegram login (first run only, per machine)

The first time you click Start, the app will ask for:
1. A confirmation code Telegram sends to your phone/app
2. Your two-step verification password, if you have one set

After that, it stays logged in (the session is saved in the `data`
folder next to the app), so you won't be asked again on that machine.

## 6. Using it day-to-day

- Click **Start bot** when you want it tracking updates in the group.
- Click **Stop bot** when you're done — it won't run in the background
  after you close it, exactly as you asked.
- The **Live activity** log on the Dashboard tab shows what it's doing.
- Every day at 9:00 PM, it automatically builds each person's PDF report,
  emails it, and uploads it to your Drive folder.
- Typing `/report_now` in the group chat regenerates a report on demand
  for whoever last posted an update.

## Where everything is stored

Right next to the app (wherever you unzipped it):
- `data/` — the SQLite database, Telegram session, Google Drive token
- `config/` — your saved settings (`settings.json`)
- `reports/` — every generated PDF report
- `logs/` — a plain-text copy of the activity log

Back up or move the whole folder together if you ever move to a new PC —
just re-run `/api/telegram/...` login and Drive connect once on the new
machine (session files don't transfer automatically for security, but you
can copy the `data` folder over if you want to skip re-login).

## What changed from the Docker version

- No `docker-compose`, no `Dockerfile`, no container — this is a normal
  packaged Python app.
- `.env` is gone — all settings are entered through the Settings tab and
  saved to `config/settings.json`.
- Telegram login (phone/code/2FA) happens through the browser instead of
  a terminal prompt, since a packaged app has no terminal.
- The old `run_automation.py` at the project root (which emailed a fake
  test update every day at 7 PM) was dropped — it looked like leftover
  test code, not something you actually wanted running. The real nightly
  report job (9 PM, real data, per-employee PDFs + Drive upload) is intact
  inside `worker.py`, unchanged in behavior from `run_listener.py`.
