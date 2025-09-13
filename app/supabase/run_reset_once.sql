-- One-off execution of the new prune + daily reset routine
-- Safe to re-run; reset portion is idempotent per UTC day.
SELECT public.reset_all_user_credits_midnight();