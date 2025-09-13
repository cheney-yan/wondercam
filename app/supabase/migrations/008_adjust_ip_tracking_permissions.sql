-- 008_adjust_ip_tracking_permissions.sql
-- Purpose: Allow anonymous (anon) users to record their last login IP.
-- Previous migration 007 granted EXECUTE only to authenticated and only
-- granted SELECT to anon on user_login_meta. Anonymous tracking therefore failed.
--
-- Changes:
--   1. Grant INSERT/UPDATE on public.user_login_meta to anon.
--   2. Grant EXECUTE on function public.set_last_login_ip(TEXT) to anon.
--   3. (Idempotent: uses GRANT which is safe if privileges already exist.)
--
-- No schema changes; pure permission adjustment.

GRANT INSERT, UPDATE ON public.user_login_meta TO anon;
GRANT EXECUTE ON FUNCTION public.set_last_login_ip(TEXT) TO anon;

COMMENT ON FUNCTION public.set_last_login_ip(TEXT) IS
'Upserts last login IP + timestamp for the current user (anonymous or authenticated) into public.user_login_meta.';