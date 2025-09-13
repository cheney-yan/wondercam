-- 007_add_last_login_ip.sql (revised)
-- Previous attempt to ALTER auth.users failed due to ownership restrictions.
-- This migration introduces a dedicated metadata table to track last login IP
-- and timestamp without modifying Supabase's managed auth.users table.
--
-- Design:
--   Table: public.user_login_meta
--     user_id        (PK, FK -> auth.users.id ON DELETE CASCADE)
--     last_login_ip  (INET)
--     last_login_at  (TIMESTAMPTZ, last time we recorded a login)
--     updated_at     (TIMESTAMPTZ, auto updated via trigger)
--
--   RPC: public.set_last_login_ip(p_ip TEXT)
--     - Upserts (INSERT … ON CONFLICT) a row for auth.uid()
--     - Stores sanitized / trimmed IP (NULL if blank)
--     - Updates last_login_ip & last_login_at
--
--   SECURITY:
--     - SECURITY DEFINER to allow updating meta row
--     - Ensures auth.uid() is present
--
--   USAGE (client/server after successful auth):
--     await supabase.rpc('set_last_login_ip', { p_ip: clientIp });
--
--   NOTE:
--     If you already have reverse proxy adding X-Forwarded-For, capture it
--     in your middleware / edge function and pass in.
--
------------------------------------------------------------
-- 1. Create table (idempotent)
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_login_meta (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    last_login_ip INET,
    last_login_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_login_meta IS
'Per-user login metadata (IP + timestamp) separate from auth.users.';
COMMENT ON COLUMN public.user_login_meta.last_login_ip IS
'Most recently recorded client IP (INET, supports IPv4 & IPv6).';

------------------------------------------------------------
-- 2. updated_at trigger
------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_login_meta_updated_at ON public.user_login_meta;
CREATE TRIGGER trg_user_login_meta_updated_at
    BEFORE UPDATE ON public.user_login_meta
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

------------------------------------------------------------
-- 3. RPC function to record last login IP
------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_last_login_ip(p_ip TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_ip INET;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No authenticated user in context';
    END IF;

    IF p_ip IS NOT NULL AND trim(p_ip) <> '' THEN
        v_ip := trim(p_ip)::INET;
    ELSE
        v_ip := NULL;
    END IF;

    INSERT INTO public.user_login_meta (user_id, last_login_ip, last_login_at)
    VALUES (auth.uid(), v_ip, NOW())
    ON CONFLICT (user_id)
    DO UPDATE SET
        last_login_ip = EXCLUDED.last_login_ip,
        last_login_at = NOW();

END;
$$;

COMMENT ON FUNCTION public.set_last_login_ip(TEXT) IS
'Upserts last login IP + timestamp for the current user into public.user_login_meta.';

------------------------------------------------------------
-- 4. Indexes (optional, cheap)
------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_user_login_meta_last_login_at
    ON public.user_login_meta (last_login_at DESC);

------------------------------------------------------------
-- 5. Permissions
------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON public.user_login_meta TO authenticated;
GRANT SELECT ON public.user_login_meta TO anon;
GRANT EXECUTE ON FUNCTION public.set_last_login_ip(TEXT) TO authenticated;

-- (Intentionally omit EXECUTE to anon; anonymous users must auth to persist.)

------------------------------------------------------------
-- 6. (Optional) Manual test:
-- SELECT public.set_last_login_ip('203.0.113.42');
-- SELECT * FROM public.user_login_meta LIMIT 5;
------------------------------------------------------------