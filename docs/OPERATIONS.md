# Gym Tracker — operations

Live state and how to keep it running. Secret values are never written here.

## Where it runs

| What | Where |
|---|---|
| App | https://gym-tracker-gcy45fsdkq-lm.a.run.app (Cloud Run `gym-tracker`) |
| GCP project | `gym-tracker-480502`, region `europe-central2` |
| Billing account | `01F7FF-EE2A00-817F1D` (the old `015E78-5F4016-A73C41` is closed) |
| Database | Firestore (default database) in the same project |
| Scraper | **Off** (archive mode, see below). Cloud Scheduler `gym-data-collector` is paused |
| Deploy | GitHub Actions on merge to `main` (`main` requires a PR) |

The admin account is `admin`; its password comes from the `ADMIN_PASSWORD` env var on the Cloud Run
service (read it with `gcloud run services describe gym-tracker --project gym-tracker-480502
--region europe-central2`). Passwords are bcrypt hashes in Firestore and cannot be recovered, only reset.

## Cost guards

- Scales to 0 when idle, max 3 instances.
- Budget 5 PLN/month, e-mail alerts at 50/90/100 % actual and 100 % forecast.
- Artifact Registry keeps only the 3 newest images.

## Revival 2026-10-29

- **Billing** — the project was linked to a closed billing account; Cloud Run and the scraper stopped on
  2026-08-03 ~22:00 (data gap from then on). Linked to the open account; Firestore data intact
  (237 days of entries 2025-12-09 → 2026-08-03, 3,746 hourly records, 6 users, 87 workouts).
- **Code (PR #44)** — scraper parsing extracted to `parse_entries_count()` with tests; a failing source
  is retried at most once per 30 s instead of on every request; no exception text in API responses;
  header shows `--` and a grey dot when the scraper fails instead of a fake live `0`. 35 tests.
- **GitHub** — the Security Scan workflow had been auto-disabled for inactivity; re-enabled.

## Archive mode (2026-11-21)

The club removed the live counter from `/na-terenie-klubu` (the page still loads after login, but the
widget is gone; the scraper never succeeded after the 2026-10-29 revival). There will be no new source,
so the app is now an archive:

- `SCRAPER_ENABLED` env var (default off): no background scraper thread, `/api/occupancy` and
  `/api/refresh` return `{"status": "archived"}` without logging in to eFitness.
- Cloud Scheduler `gym-data-collector` paused
  (`gcloud scheduler jobs resume gym-data-collector --project gym-tracker-480502 --location europe-central2` to undo).
- Occupancy statistics use the whole archive (hourly data 2025-12-11 → 2026-08-03, 222 complete days)
  instead of the last 30 days. The header shows "Archiwum"; the stats tab shows the date range and the day count.
- Workouts (calendar, strength) still work as before.

## If it breaks again

- Header shows `--` during opening hours and logs say `Could not find entry numbers`: the eFitness
  page changed — update `parse_entries_count()` in `app.py` (tests in `tests/test_scraper.py`).
- **gcloud**: always pass `--project gym-tracker-480502`.
