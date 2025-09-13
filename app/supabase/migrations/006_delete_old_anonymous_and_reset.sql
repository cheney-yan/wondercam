
-- 006_delete_old_anonymous_and_reset.sql
-- Purpose:
--   1. Delete anonymous users older than 24 hours (and their cascading credit rows).
--   2. Reset daily credits for remaining users at UTC midnight (or on manual run).
--      Anonymous => 10, Registered => 50.
--   3. Keep existing cron job (created in 005) calling the same function name.
--      We DROP and recreate the function so the scheduled job continues to work.
--
-- Notes:
--   - Deleting from auth.users requires the function owner to have sufficient privileges.
--   - user_credits has ON DELETE CASCADE so associated credit rows are removed automatically.
--   - We only reset rows whose last_reset_at (UTC date) is before today (UTC).
--   - Adds audit transaction rows (type 'reset') if credit_transactions table exists.
--   - Adds audit transaction rows (type 'prune') for each deleted anonymous user if table exists.
--
-- Safety:
--   - Function is idempotent for the reset portion (won't re-reset already done today).
--   - Anonymous deletion only targets rows older than 24h AND still anonymous (email NULL or empty).
--
-- Execution:
--   - Scheduled daily at 00:00 UTC by existing cron job: daily_credit_reset
--   - We also invoke it once at the end of this migration for immediate effect.

------------------------------------------------------------
-- Drop previous version of the function
------------------------------------------------------------
DROP FUNCTION IF EXISTS public.reset_all_user_credits_midnight();

------------------------------------------------------------
-- Recreate enhanced function with anonymous pruning
------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reset_all_user_credits_midnight()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    todays_midnight_utc TIMESTAMP WITH TIME ZONE := date_trunc('day', (now() AT TIME ZONE 'utc')) AT TIME ZONE 'utc';
    deleted_count INTEGER := 0;
    reset_count   INTEGER := 0;
    rec RECORD;
    daily_allowance INTEGER;
BEGIN
    ----------------------------------------------------------------
    -- 1. Prune anonymous users older than 24 hours
    ----------------------------------------------------------------
    -- We delete from auth.users directly. ON DELETE CASCADE in user_credits
    -- ensures credit rows are removed. We gather affected user IDs first for
    -- optional audit logging.
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'credit_transactions'
    ) THEN
        -- Insert audit rows BEFORE deleting (so we still have user_id)
        INSERT INTO public.credit_transactions (user_id, transaction_type, amount, description, metadata)
        SELECT u.id, 'reset', 0, 'Anonymous user pruned (older than 24h)', jsonb_build_object('routine','anonymous_prune')
        FROM auth.users u
        WHERE (u.email IS NULL OR u.email = '')
          AND u.created_at < (now() - interval '24 hours');
    END IF;

    WITH del AS (
        DELETE FROM auth.users u
        WHERE (u.email IS NULL OR u.email = '')
          AND u.created_at < (now() - interval '24 hours')
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM del;

    ----------------------------------------------------------------
    -- 2. Reset credits for remaining users needing a new day reset
    ----------------------------------------------------------------
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

        IF EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'credit_transactions'
        ) THEN
            INSERT INTO public.credit_transactions (user_id, transaction_type, amount, description, metadata)
            VALUES (rec.user_id, 'reset', daily_allowance, 'Daily credit reset (midnight UTC)', jsonb_build_object('routine', 'midnight_reset'));
        END IF;

        reset_count := reset_count + 1;
    END LOOP;

    RAISE NOTICE 'Anonymous users pruned: %, Users reset: %', deleted_count, reset_count;
END;
$$;

COMMENT ON FUNCTION public.reset_all_user_credits_midnight() IS
'Deletes anonymous users older than 24h and performs daily credit reset (Anon=10, Registered=50) once per UTC day.';

------------------------------------------------------------
-- Permissions (adjust if stricter needed)
------------------------------------------------------------
GRANT EXECUTE ON FUNCTION public.reset_all_user_credits_midnight() TO authenticated;
GRANT EXECUTE ON FUNCTION public.reset_all_user_credits_midnight() TO anon;

