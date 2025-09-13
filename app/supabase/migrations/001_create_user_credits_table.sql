-- Create user_credits table with RLS policies
-- This migration creates the credit tracking system for WonderCam

-- Create user_credits table
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    total_credits INTEGER NOT NULL DEFAULT 10,
    used_credits INTEGER NOT NULL DEFAULT 0,
    remaining_credits INTEGER NOT NULL DEFAULT 10,
    last_reset_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique index to prevent duplicate user entries
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_user_credits_last_reset ON user_credits(last_reset_at);

-- Enable Row Level Security (RLS)
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: Users can only see their own credits
CREATE POLICY "Users can view own credits" ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

-- Create RLS policy: Users can update their own credits
CREATE POLICY "Users can update own credits" ON user_credits
    FOR UPDATE USING (auth.uid() = user_id);

-- Create RLS policy: Users can insert their own credits
CREATE POLICY "Users can insert own credits" ON user_credits
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Create RLS policy: Users can delete their own credits
CREATE POLICY "Users can delete own credits" ON user_credits
    FOR DELETE USING (auth.uid() = user_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_user_credits_updated_at 
    BEFORE UPDATE ON user_credits 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to initialize credits for new users
CREATE OR REPLACE FUNCTION initialize_user_credits()
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

    -- Insert initial credits for the new user
    INSERT INTO public.user_credits (user_id, total_credits, used_credits, remaining_credits, last_reset_at)
    VALUES (NEW.id, initial_credits, 0, initial_credits, NOW());
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to initialize credits when user is created
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION initialize_user_credits();

-- Create function to reset daily credits
CREATE OR REPLACE FUNCTION reset_daily_credits()
RETURNS void AS $$
DECLARE
    user_record RECORD;
BEGIN
    -- Loop through users whose credits need resetting
    FOR user_record IN
        SELECT uc.user_id, u.email, u.is_anonymous
        FROM public.user_credits uc
        JOIN auth.users u ON uc.user_id = u.id
        WHERE uc.last_reset_at < (NOW() - INTERVAL '24 hours')
    LOOP
        -- Reset credits based on user type
        UPDATE public.user_credits
        SET
            total_credits = CASE
                WHEN user_record.is_anonymous OR user_record.email IS NULL THEN 10  -- Anonymous users
                ELSE 50  -- Registered users
            END,
            used_credits = 0,
            remaining_credits = CASE
                WHEN user_record.is_anonymous OR user_record.email IS NULL THEN 10
                ELSE 50
            END,
            last_reset_at = NOW()
        WHERE user_id = user_record.user_id;
    END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions
GRANT ALL ON user_credits TO authenticated;
GRANT ALL ON user_credits TO anon;

-- Comment the table and columns for documentation
COMMENT ON TABLE user_credits IS 'Stores credit balances for users. Anonymous users get 10 credits daily, registered users get 50 credits daily.';
COMMENT ON COLUMN user_credits.user_id IS 'Foreign key to auth.users. Links credit balance to user account.';
COMMENT ON COLUMN user_credits.remaining_credits IS 'Current credit balance. Each photo processing costs 2 credits.';
COMMENT ON COLUMN user_credits.last_reset_at IS 'Timestamp when credits were last reset. Used for daily credit refresh.';