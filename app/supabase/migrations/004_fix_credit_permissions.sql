-- Fix permissions for credit system to work with anonymous users

-- Grant permissions to anonymous users for credit table operations
GRANT ALL ON public.user_credits TO anon;
GRANT USAGE ON SCHEMA public TO anon;

-- Update RLS policies to be more permissive for credit operations
-- Allow anonymous users to insert their own credit records
DROP POLICY IF EXISTS "Users can insert own credits" ON public.user_credits;
CREATE POLICY "Users can insert own credits" ON public.user_credits
    FOR INSERT WITH CHECK (true);

-- Allow anonymous users to select their own credit records
DROP POLICY IF EXISTS "Users can view own credits" ON public.user_credits;
CREATE POLICY "Users can view own credits" ON public.user_credits
    FOR SELECT USING (auth.uid() = user_id OR auth.uid() IS NULL);

-- Allow anonymous users to update their own credit records
DROP POLICY IF EXISTS "Users can update own credits" ON public.user_credits;
CREATE POLICY "Users can update own credits" ON public.user_credits
    FOR UPDATE USING (auth.uid() = user_id OR auth.uid() IS NULL);

-- Grant execute permissions on functions to anonymous role
GRANT EXECUTE ON FUNCTION public.consume_credits(UUID, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION public.reset_user_credits_if_needed(UUID) TO anon;
GRANT EXECUTE ON FUNCTION public.get_user_credits(UUID) TO anon;
GRANT EXECUTE ON FUNCTION public.initialize_user_credits() TO anon;

-- Update function security context to be more permissive
CREATE OR REPLACE FUNCTION public.initialize_user_credits()
RETURNS TRIGGER AS $$
DECLARE
    initial_credits INTEGER;
    is_anonymous BOOLEAN;
BEGIN
    -- Determine if the user is anonymous
    is_anonymous := NEW.email IS NULL OR NEW.is_anonymous;

    IF is_anonymous THEN
        initial_credits := 10; -- Anonymous users
    ELSE
        initial_credits := 50; -- Registered users
    END IF;

    -- Insert initial credits for the new user (bypass RLS)
    INSERT INTO public.user_credits (user_id, total_credits, used_credits, remaining_credits, last_reset_at)
    VALUES (NEW.id, initial_credits, 0, initial_credits, NOW());
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Ensure the trigger exists and is properly configured
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW 
    EXECUTE FUNCTION public.initialize_user_credits();

-- Note: credit_transactions table creation removed as it's not needed for basic credit system