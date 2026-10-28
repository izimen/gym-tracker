# Gym Tracker — operations

Live state and how to keep it running. Secret values are never written here.

## Where it runs

| What | Where |
|---|---|
| App | https://gym-tracker-gcy45fsdkq-lm.a.run.app (Cloud Run `gym-tracker`) |
| GCP project | `gym-tracker-480502`, region `europe-central2` |
| Billing account | `01F7FF-EE2A00-817F1D` (the old `015E78-5F4016-A73C41` is closed) |
| Database | Firestore (default database) in the same project |
| Scraper | Cloud Scheduler `gym-data-collector`, every 10 min, 06:00–22:59 Europe/Warsaw |
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

## If it breaks again

- Header shows `--` during opening hours and logs say `Could not find entry numbers`: the eFitness
  page changed — update `parse_entries_count()` in `app.py` (tests in `tests/test_scraper.py`).
- Statistics tab says "Zbieranie danych…": it averages the last 30 days; it fills in after collection resumes.
- **gcloud**: always pass `--project gym-tracker-480502`.
