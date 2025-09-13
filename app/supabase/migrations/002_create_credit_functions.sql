-- Create stored procedures for atomic credit operations
-- This migration creates the functions needed for safe credit management

-- Function to atomically consume credits
CREATE OR REPLACE FUNCTION consume_credits(
    p_user_id UUID,
    p_amount INTEGER DEFAULT 2
)
RETURNS JSON AS $$
DECLARE
    current_remaining INTEGER;
    current_used INTEGER;
    result JSON;
BEGIN
    -- Check if daily reset is needed first
    PERFORM reset_user_credits_if_needed(p_user_id);
    
    -- Lock the row and get current credits
    SELECT remaining_credits, used_credits INTO current_remaining, current_used
    FROM public.user_credits
    WHERE user_id = p_user_id
    FOR UPDATE;
    
    -- Check if user exists
    IF NOT FOUND THEN
        RETURN json_build_object(
            'success', false,
            'error', 'User not found',
            'credits_remaining', 0
        );
    END IF;
    
    -- Check if enough credits available
    IF current_remaining < p_amount THEN
        RETURN json_build_object(
            'success', false,
            'error', 'Insufficient credits',
            'credits_remaining', current_remaining,
            'credits_needed', p_amount
        );
    END IF;
    
    -- Consume the credits
    UPDATE public.user_credits
    SET
        remaining_credits = current_remaining - p_amount,
        used_credits = current_used + p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    -- Return success with remaining credits
    RETURN json_build_object(
        'success', true,
        'credits_consumed', p_amount,
        'credits_remaining', current_remaining - p_amount
    );
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM,
            'credits_remaining', 0
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check and reset credits for a specific user if needed
CREATE OR REPLACE FUNCTION reset_user_credits_if_needed(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    user_email TEXT;
    current_date_val DATE := CURRENT_DATE;
    credits_reset BOOLEAN := FALSE;
BEGIN
    -- Get user email to determine credit amount
    SELECT u.email INTO user_email
    FROM auth.users u
    WHERE u.id = p_user_id;
    
    -- Check if reset is needed and perform it atomically
    UPDATE public.user_credits
    SET
        total_credits = CASE
            WHEN user_email IS NULL OR user_email = '' THEN 10  -- Anonymous users
            ELSE 50  -- Registered users
        END,
        used_credits = 0,
        remaining_credits = CASE
            WHEN user_email IS NULL OR user_email = '' THEN 10
            ELSE 50
        END,
        last_reset_at = NOW()
    WHERE
        user_id = p_user_id
        AND last_reset_at < (NOW() - INTERVAL '24 hours');
    
    -- Check if any rows were updated
    credits_reset := FOUND;
    
    RETURN credits_reset;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get current credits with automatic reset
CREATE OR REPLACE FUNCTION get_user_credits(p_user_id UUID)
RETURNS JSON AS $$
DECLARE
    user_credits_record RECORD;
    was_reset BOOLEAN;
BEGIN
    -- Reset credits if needed
    SELECT reset_user_credits_if_needed(p_user_id) INTO was_reset;
    
    -- Get current credits
    SELECT uc.remaining_credits, uc.last_reset_at, u.email, u.is_anonymous
    INTO user_credits_record
    FROM public.user_credits uc
    JOIN auth.users u ON uc.user_id = u.id
    WHERE uc.user_id = p_user_id;
    
    -- Return credits info
    IF FOUND THEN
        RETURN json_build_object(
            'credits', user_credits_record.remaining_credits,
            'last_reset_date', user_credits_record.last_reset_at,
            'is_anonymous', (user_credits_record.is_anonymous OR user_credits_record.email IS NULL),
            'was_reset', was_reset
        );
    ELSE
        RETURN json_build_object(
            'credits', 0,
            'error', 'User not found',
            'was_reset', false
        );
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'credits', 0,
            'error', SQLERRM,
            'was_reset', false
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to add credits (for admin or upgrade scenarios)
CREATE OR REPLACE FUNCTION add_credits(
    p_user_id UUID,
    p_amount INTEGER
)
RETURNS JSON AS $$
DECLARE
    new_credits INTEGER;
BEGIN
    -- Add credits atomically
    UPDATE public.user_credits
    SET
        total_credits = total_credits + p_amount,
        remaining_credits = remaining_credits + p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id
    RETURNING remaining_credits INTO new_credits;
    
    IF FOUND THEN
        RETURN json_build_object(
            'success', true,
            'credits_added', p_amount,
            'new_total', new_credits
        );
    ELSE
        RETURN json_build_object(
            'success', false,
            'error', 'User not found'
        );
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to upgrade anonymous user to registered (preserving credits)
CREATE OR REPLACE FUNCTION upgrade_anonymous_to_registered(
    p_user_id UUID,
    p_new_email TEXT
)
RETURNS JSON AS $$
DECLARE
    current_credits INTEGER;
    upgraded_credits INTEGER;
BEGIN
    -- Get current credits
    SELECT remaining_credits INTO current_credits
    FROM public.user_credits
    WHERE user_id = p_user_id;
    
    IF NOT FOUND THEN
        RETURN json_build_object(
            'success', false,
            'error', 'User credits not found'
        );
    END IF;
    
    -- Calculate upgraded credits (registered users get more)
    -- Keep existing credits but ensure minimum 50 for registered users
    upgraded_credits := GREATEST(current_credits, 50);
    
    -- Update credits to registered user level
    UPDATE public.user_credits
    SET
        total_credits = upgraded_credits,
        remaining_credits = upgraded_credits,
        updated_at = NOW()
    WHERE user_id = p_user_id;
    
    RETURN json_build_object(
        'success', true,
        'previous_credits', current_credits,
        'new_credits', upgraded_credits,
        'credits_bonus', upgraded_credits - current_credits
    );
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function for batch credit reset (for scheduled jobs)
CREATE OR REPLACE FUNCTION batch_reset_daily_credits()
RETURNS JSON AS $$
DECLARE
    users_reset INTEGER := 0;
    user_record RECORD;
BEGIN
    -- Loop through users who need credit reset
    FOR user_record IN 
        SELECT uc.user_id, u.email
        FROM user_credits uc
        JOIN auth.users u ON uc.user_id = u.id
        WHERE uc.last_reset_date < CURRENT_DATE
    LOOP
        -- Reset credits for this user
        UPDATE user_credits 
        SET 
            credits = CASE 
                WHEN user_record.email IS NULL OR user_record.email = '' THEN 10  -- Anonymous
                ELSE 50  -- Registered
            END,
            last_reset_date = CURRENT_DATE,
            updated_at = NOW()
        WHERE user_id = user_record.user_id;
        
        users_reset := users_reset + 1;
    END LOOP;
    
    RETURN json_build_object(
        'success', true,
        'users_reset', users_reset,
        'reset_date', CURRENT_DATE
    );
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN json_build_object(
            'success', false,
            'error', SQLERRM,
            'users_reset', users_reset
        );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION consume_credits(UUID, INTEGER) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION reset_user_credits_if_needed(UUID) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION get_user_credits(UUID) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION add_credits(UUID, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION upgrade_anonymous_to_registered(UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION batch_reset_daily_credits() TO authenticated;

-- Add comments for documentation
COMMENT ON FUNCTION consume_credits(UUID, INTEGER) IS 'Atomically consume credits for a user. Returns success status and remaining credits.';
COMMENT ON FUNCTION reset_user_credits_if_needed(UUID) IS 'Check if user needs daily credit reset and perform it if needed.';
COMMENT ON FUNCTION get_user_credits(UUID) IS 'Get current user credits with automatic daily reset check.';
COMMENT ON FUNCTION add_credits(UUID, INTEGER) IS 'Add credits to a user account (admin function).';
COMMENT ON FUNCTION upgrade_anonymous_to_registered(UUID, TEXT) IS 'Upgrade anonymous user to registered, preserving existing credits with minimum 50.';
COMMENT ON FUNCTION batch_reset_daily_credits() IS 'Reset daily credits for all users (scheduled job function).';