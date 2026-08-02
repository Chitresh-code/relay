-- One-time setup: schedules a daily pg_cron job in Neon that purges chat transcripts older
-- than 90 days (ARCHITECTURE.md §12, §4/§8). Run this once against your Neon database (Neon
-- SQL editor, or `psql "$DATABASE_URL" -f backend/scripts/retention_purge.sql`) — not run
-- automatically by the app, since CREATE EXTENSION/cron.schedule need a privileged role that
-- not every DATABASE_URL grants (Neon's default connection role does).
--
-- Caveat: pg_cron only fires while compute is active — on Neon's free-tier scale-to-zero, a
-- purge can be skipped while the branch is suspended. Acceptable for a personal-scale app;
-- pin the branch always-on if you need it guaranteed.
--
-- escalations/leads are NOT touched (PRD §4 — only the raw transcript is time-limited).

CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'relay-retention-purge') THEN
        PERFORM cron.schedule(
            'relay-retention-purge',
            '0 3 * * *',
            $job$DELETE FROM messages WHERE created_at < now() - interval '90 days'$job$
        );
    END IF;
END $$;
