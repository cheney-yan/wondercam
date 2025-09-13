-- 005_add_daily_credit_reset_routine.sql
-- Purpose: Introduce a deterministic midnight (00:00 UTC) daily credit reset routine
-- for all users, replacing the older ad-hoc / per-request 24h logic and the
-- outdated batch_reset_daily_credits function definition.

-- =========================================================
-- Safety / prerequisites
-- =========================================================
-- Ensure pg_cron extension exists (Supabase exposes it in the extensions schema)
CREATE EXTENSION IF NOT EXISTS pg_cron WITH SCHEMA extensions;

-- =========================================================
-- Housekeeping: drop obsolete / inconsistent function
-- (The previous batch_reset_daily_credits() referenced non-existent columns
-- like last_reset_date / credits. We remove it to avoid confusion.)
-- =========================================================
DROP FUNCTION IF EXISTS public.batch_reset_daily_credits();

-- =========================================================
-- Core reset function
-- Resets credits once per UTC day (idempotent if re-run the same day).
-- Logic:
--   Anonymous (email IS NULL or empty) => 10 daily credits
--   Registered (email present)         => 50 daily credits
-- Only rows whose last_reset_at day (UTC) is before "today" (UTC) are updated.
-- Sets:
--   total_credits       = daily allowance
--   used_credits        = 0
--   remaining_credits   = daily allowance
--   last_reset_at       = current day boundary (UTC midnight)
-- Also inserts a 'reset' transaction record for auditing.
-- =========================================================
CREATE OR REPLACE FUNCTION public.reset_all_user_credits_midnight()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    todays_midnight_utc TIMESTAMP WITH TIME ZONE := date_trunc('day', (now() AT TIME ZONE 'utc')) AT TIME ZONE 'utc';
    rec RECORD;
    daily_allowance INTEGER;
BEGIN
    FOR rec IN
        SELECT uc.user_id, u.email
        FROM public.user_credits uc
        JOIN auth.users u ON u.id = uc.user_id
        WHERE date_trunc('day', uc.last_reset_at AT TIME ZONE 'utc') < todays_midnight_utc
        FOR UPDATE
    LOOP
        daily_allowance := CASE
            WHEN rec.email IS NULL OR rec.email = '' THEN 10
            ELSE 50
        END;

        UPDATE public.user_credits
        SET
            total_credits     = daily_allowance,
            used_credits      = 0,
            remaining_credits = daily_allowance,
            last_reset_at     = todays_midnight_utc,
            updated_at        = now()
        WHERE user_id = rec.user_id;

        -- Insert audit transaction (optional table; only if it exists)
        -- If credit_transactions table is not present in current deployment,
        -- this INSERT will fail; so we guard with EXISTS.
        IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'credit_transactions'
        ) THEN
            INSERT INTO public.credit_transactions (user_id, transaction_type, amount, description, metadata)
            VALUES (rec.user_id, 'reset', daily_allowance, 'Daily credit reset (midnight UTC)', jsonb_build_object('routine', 'midnight_reset'));
        END IF;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION public.reset_all_user_credits_midnight() IS
'Resets all user credits once per UTC day at 00:00. Anonymous=10, Registered=50. Idempotent for a given UTC day.';

-- =========================================================
-- Permissions (only service / backend contexts truly need this,
-- but we allow authenticated and anon to execute harmlessly if required
-- for debugging / manual invocation - adjust if stricter policy desired).
-- =========================================================
GRANT EXECUTE ON FUNCTION public.reset_all_user_credits_midnight() TO authenticated;
GRANT EXECUTE ON FUNCTION public.reset_all_user_credits_midnight() TO anon;

-- =========================================================
-- Schedule via pg_cron:
--   Runs daily at 00:00 UTC
-- If job already exists, we update it to ensure correct command / schedule.
-- =========================================================
DO $$
DECLARE
    existing_job_id INTEGER;
BEGIN
    SELECT jobid INTO existing_job_id
    FROM cron.job
    WHERE jobname = 'daily_credit_reset';

    IF existing_job_id IS NULL THEN
        PERFORM cron.schedule(
            'daily_credit_reset',
            '0 0 * * *',  -- minute hour dom month dow (UTC)
            'SELECT public.reset_all_user_credits_midnight();'
        );
    ELSE
        -- Ensure schedule & command remain correct
        PERFORM cron.alter_job(
            existing_job_id,
            '0 0 * * *',
            'SELECT public.reset_all_user_credits_midnight();'
        );
    END IF;
END;
$$;

-- =========================================================
-- Manual invocation helper (optional):
--   SELECT public.reset_all_user_credits_midnight();
-- =========================================================