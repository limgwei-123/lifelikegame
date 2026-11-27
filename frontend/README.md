# Lifelikegame frontend

React Native + Expo Router + TypeScript; one codebase for Android and Web.
Packages 1–4 include email authentication, session handling, shared UI/theme,
首页 / 冒险 / 我的 navigation, real homepage task workflows, boss adventure, and
account/appearance settings. Management and AI follow packages 5–6 in the local plan.

My opens profile, password and appearance sheets. Nickname, built-in avatar and
IANA timezone save through `PATCH /users/me`, sharing the serialized authenticated
queue with task reads/writes to avoid stale profile/balance updates. A timezone
change refreshes the server's player date/progress. The approved adventurer art
is reused with small badges for the existing `leaf/tree/sun/book` avatar keys.
Email is displayed; changing email and Google login remain outside this round.

Password changes call the existing endpoint, clear the local session on success
and return to login; the backend revokes old credentials. Wrong current passwords
stay in the form. Passwords are never saved in snapshots, preferences or storage.

Appearance supports light/dark/system and blue/green/purple/orange accents, saved
per device/browser as `lifelikegame_appearance_v1`. Web uses localStorage; native
uses a separate SecureStore key. It survives logout and is intentionally shared
by accounts on that device. Invalid stored formats fall back to system/blue;
storage failures keep the last saved settings and show a retry message. No new
backend schema or cross-device theme sync is required.

Adventure displays `/progress` HP, round, position and roster in a full page and
a compact homepage card. All six original illustrations are bundled under
`assets/bosses/`, keyed by the backend boss IDs. Goal completions can show a
single short hit/defeat notification; todos never fabricate damage. Refresh,
navigation and account changes do not replay awards. Feedback only describes a
confirmed server transition, and all gameplay mutations remain backend-owned.
Animations respect Web/native reduced-motion preferences, stop on cleanup and
run only for completion feedback; there are no idle animation loops.

The homepage uses the server's player date, streak and balance; shows overdue
pending work today; supports once/daily/weekly/monthly task creation, optional
goals and scoring schemes, snapshot scoring, completion-driven recurrence,
task edits, pause/resume and deletion. Date/month browsing only reads records.
Entry/resume may repair current work once per player day; rule changes and
restoring a paused task explicitly repair it as part of that action. No timer
or frontend midnight scheduler runs.

Task text and repeating rules are saved separately because the backend exposes
separate writes. Rule changes apply to subsequent occurrences; existing current
dates are retained. One-time dates are chosen when creating a task. Deleted task
completions remain history and display “已删除的任务” because their original title
is not stored in the occurrence response. A completion's real action date drives
streaks and today's count; its scheduled date remains the history/calendar date.

## Start Web

Use Node 24.3+ (this checkout was verified on 24.20) and a running Docker backend.
From the project root, check `docker info` first. If Docker is unavailable, stop
and ask the user to start it. Do not automatically migrate an existing database.
The backend schema must already match its current Alembic head.

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run web
```

Open http://localhost:5173. Set `EXPO_PUBLIC_API_URL` in `.env.local` to the actual
API origin and restart Expo after changing it. The old `VITE_API_BASE_URL` is no
longer used. EXPO_PUBLIC variables are bundled public configuration, never secrets.

For Web in Docker, rebuild the frontend and replace the old dependency volume:

```powershell
docker compose up -d --build --renew-anon-volumes frontend
```

The Compose API/database must already be usable. Production Web hosting needs
SPA fallback to `index.html` for `/login`, `/me` and other Expo routes, plus an
explicit HTTPS API URL and backend CORS origin. `dist/` is generated, not source.

## Android

Run Expo on the host, not inside the Web container:

```powershell
cd frontend
npm run android
```

This opens an available Android emulator/device. Alternatively run `npm run dev`
and scan the QR code with a compatible Expo Go build on the same LAN. Configure
`EXPO_PUBLIC_API_URL=http://10.0.2.2:8000` for the Android emulator, or your PC's
LAN IP for a physical phone. A phone's localhost refers to the phone itself.
Without an explicit URL, development uses Metro's host with port 8000.
For a release build always configure the real HTTPS API URL; do not use a local
review URL. Store signing and Google Play publication are outside package 1.

Native credentials use Expo SecureStore. Web uses sessionStorage: refresh restores
the session in that tab, closing the tab ends its storage lifetime. Passwords are
never stored. Expired tokens return to login; temporary connectivity failures offer
retry rather than discarding a saved session. There is no refresh-token endpoint.

## Verification

```powershell
npm test
npm run typecheck
npm run build
npm run build:android
npx expo install --check
```

Android export checks the bundle; it does not replace a real device test or create
a signed APK/AAB. Builds write ignored `dist/` and `dist-android/` directories.

Dependency audit currently reports a moderate glob-pattern denial-of-service
advisory in Expo's fingerprint tooling (`@expo/fingerprint` → `minimatch@10`).
It is build tooling, not the app's task or authentication path. npm's proposed
automatic fix downgrades Expo to SDK 52, so it is not applied. Recheck when
updating Expo; do not use `npm audit fix --force` on the locked SDK blindly.

Optional browser integration, with Web running and **only a disposable backend**
configured in `.env.local` (creates one test account per run):

```powershell
npx playwright install chromium
$env:E2E_DISPOSABLE_API = '1'
$env:E2E_API_URL = 'http://localhost:8001'
npx playwright test
```

Set `E2E_BROWSER_CHANNEL=msedge` to use installed Edge instead of downloading
Chromium. Test results and screenshots are ignored. The suite covers real signup,
wrong/correct password, three tabs, refresh, logout and protected links; it
simulates only the `/users/me` expired-token response. The task workflow creates
its own test account/data in that disposable API and covers plain/scored tasks,
snapshots, daily/weekly/monthly rules, next occurrences, overdue work, editing,
pause/resume/delete and a simulated failed completion. It never targets the
existing development database automatically. The adventure suite additionally
uses real workflow/completion APIs to finish the first six bosses, verifies the
second-round slime at 32 HP, and checks reduced motion and account isolation.
The account suite also verifies profile persistence/validation/failure, timezone
dates, live system appearance, real browser-storage errors and password revocation.
