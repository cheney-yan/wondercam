'use client';

import { createClient } from '@/lib/supabase/client';
import { anonymousAuthService } from './anonymous-auth';

export enum CreditAction {
  PHOTO_PROCESSING = 'photo_processing', // 2 credits when AI response is returned (legacy initial analysis)
  IMAGE_GENERATION = 'image_generation', // 2 credits per generated image
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  transaction_type: 'earned' | 'spent' | 'bonus' | 'reset';
  amount: number;
  description: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface CreditCache {
  credits: number;
  timestamp: number;
  userId: string;
}

export interface CreditService {
  getCurrentCredits(): Promise<number>;
  consumeCredits(amount: number, action: CreditAction): Promise<boolean>;
  checkCanPerformAction(action: CreditAction): Promise<boolean>;
  refreshDailyCredits(): Promise<void>;
  getTransactionHistory(): Promise<CreditTransaction[]>;
  grantBonusCredits(amount: number, reason: string): Promise<void>;
}

export class SupabaseCreditService implements CreditService {
  private supabase = createClient();
  private static CACHE_KEY = 'wondercam_credits';
  private static CACHE_TTL = 60 * 1000; // 1 minute cache

  // Credit rules based on user requirements
  private readonly CREDIT_COSTS = {
    [CreditAction.PHOTO_PROCESSING]: 2, // legacy (not auto-charged now unless used explicitly)
    [CreditAction.IMAGE_GENERATION]: 2, // per generated image
  };
  
  private readonly INITIAL_CREDITS = {
    anonymous: 1,
    registered: 50
  };
  
  private readonly DAILY_CREDITS = {
    anonymous: 10,  // Daily reset to 10 for anonymous users
    registered: 50  // Daily reset to 50 for registered users
  };

  // Client-side caching
  private getCachedCredits(): number | null {
    try {
      const cached = localStorage.getItem(SupabaseCreditService.CACHE_KEY);
      if (!cached) return null;
      
      const { credits, timestamp, userId } = JSON.parse(cached) as CreditCache;
      
      // Check if cache is still valid and for the same user
      const currentUser = anonymousAuthService.getCurrentUser();
      if (Date.now() - timestamp > SupabaseCreditService.CACHE_TTL || !currentUser) {
        return null;
      }
      
      return credits;
    } catch (error) {
      console.error('Failed to get cached credits:', error);
      return null;
    }
  }

  private setCachedCredits(credits: number, userId: string): void {
    try {
      const cache: CreditCache = {
        credits,
        timestamp: Date.now(),
        userId
      };
      localStorage.setItem(SupabaseCreditService.CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
      console.error('Failed to cache credits:', error);
    }
  }


  async getCurrentCredits(): Promise<number> {
    try {
      const user = await anonymousAuthService.getCurrentUser();
      if (!user) throw new Error('No user found');

      // Try cache first
      const cached = this.getCachedCredits();
      if (cached !== null) {
        return cached;
      }

      // Check if daily reset is needed (24h logic)
      await this.checkDailyReset(user.id);

      // Attempt to fetch credits row
      const { data, error } = await this.supabase
        .from('user_credits')
        .select('remaining_credits, total_credits')
        .eq('user_id', user.id)
        .single();

      if (error) {
        // Row missing: create it now (self-healing) with initial allowance
        if (error.code === 'PGRST116' || error.message?.includes('PGRST116') || error.details?.includes('Results contain 0 rows')) {
          console.warn('⚠️ user_credits row missing for user. Creating new credits record…', user.id);
          const isAnonymous = await anonymousAuthService.isAnonymous();
          const initial = isAnonymous
            ? this.INITIAL_CREDITS.anonymous
            : this.INITIAL_CREDITS.registered;

          const { error: insertError } = await this.supabase
            .from('user_credits')
            .insert({
              user_id: user.id,
              total_credits: initial,
              used_credits: 0,
              remaining_credits: initial,
              last_reset_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            });

          if (insertError) {
            console.error('❌ Failed to create user_credits row:', insertError);
            throw insertError;
          }

          this.setCachedCredits(initial, user.id);
          console.log('✅ Created new user_credits row with initial credits:', { userId: user.id, initial, isAnonymous });
          return initial;
        }

        // Other error bubbles up
        throw error;
      }

      const credits = data.remaining_credits;
      this.setCachedCredits(credits, user.id);
      return credits;
    } catch (error) {
      console.error('❌ Failed to get current credits:', error);
      throw error;
    }
  }

  private async checkDailyReset(userId: string): Promise<void> {
    try {
      const { data, error } = await this.supabase
        .from('user_credits')
        .select('last_reset_at')
        .eq('user_id', userId)
        .single();

      if (error) return;

      const lastReset = new Date(data.last_reset_at);
      const now = new Date();
      const timeDiff = now.getTime() - lastReset.getTime();
      const daysDiff = timeDiff / (1000 * 3600 * 24);

      // If more than 24 hours have passed, reset credits
      if (daysDiff >= 1) {
        await this.refreshDailyCredits();
      }
    } catch (error) {
      console.error('❌ Failed to check daily reset:', error);
    }
  }

  async refreshDailyCredits(): Promise<void> {
    try {
      const user = await anonymousAuthService.getCurrentUser();
      if (!user) throw new Error('No user found');

      const isAnonymous = await anonymousAuthService.isAnonymous();
      const dailyCredits = isAnonymous 
        ? this.DAILY_CREDITS.anonymous 
        : this.DAILY_CREDITS.registered;

      // Reset credits to daily amount
      const { error } = await this.supabase
        .from('user_credits')
        .update({
          total_credits: dailyCredits,
          used_credits: 0,
          remaining_credits: dailyCredits,
          last_reset_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('user_id', user.id);

      if (error) throw error;

      // Create transaction record
      await this.supabase
        .from('credit_transactions')
        .insert({
          user_id: user.id,
          transaction_type: 'reset',
          amount: dailyCredits,
          description: 'Daily credit reset'
        });

      // Clear cache to force refresh
      localStorage.removeItem(SupabaseCreditService.CACHE_KEY);

      console.log(`✅ Daily credits reset to ${dailyCredits} for user:`, user.id);
    } catch (error) {
      console.error('❌ Failed to refresh daily credits:', error);
      throw error;
    }
  }

  async consumeCredits(amount: number, action: CreditAction): Promise<boolean> {
    try {
      const response = await fetch('/api/credits/consume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, action }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        console.error('❌ Failed to consume credits:', data.error);
        return false;
      }

      // Clear cache to force refresh
      localStorage.removeItem(SupabaseCreditService.CACHE_KEY);
      window.dispatchEvent(new Event('storage'));

      console.log('✅ Successfully consumed credits:', { amount, action, remaining: data.credits_remaining });
      return true;
    } catch (error) {
      console.error('❌ Failed to consume credits:', error);
      return false;
    }
  }

  private async manualConsumeCredits(userId: string, amount: number): Promise<boolean> {
    try {
      // Get current credits with row lock
      const { data: currentData, error: selectError } = await this.supabase
        .from('user_credits')
        .select('remaining_credits, used_credits')
        .eq('user_id', userId)
        .single();

      if (selectError) throw selectError;

      const newRemaining = currentData.remaining_credits - amount;
      const newUsed = currentData.used_credits + amount;

      if (newRemaining < 0) return false;

      // Update credits
      const { error: updateError } = await this.supabase
        .from('user_credits')
        .update({
          used_credits: newUsed,
          remaining_credits: newRemaining,
          updated_at: new Date().toISOString()
        })
        .eq('user_id', userId);

      if (updateError) throw updateError;

      // Insert transaction record
      await this.supabase
        .from('credit_transactions')
        .insert({
          user_id: userId,
          transaction_type: 'spent',
          amount: amount,
          description: 'Photo processing credits'
        });

      return true;
    } catch (error) {
      console.error('❌ Manual credit consumption failed:', error);
      return false;
    }
  }

  async checkCanPerformAction(action: CreditAction): Promise<boolean> {
    try {
      const cost = this.CREDIT_COSTS[action];
      const currentCredits = await this.getCurrentCredits();
      return currentCredits >= cost;
    } catch (error) {
      console.error('❌ Failed to check if action can be performed:', error);
      return false;
    }
  }

  async grantBonusCredits(amount: number, reason: string): Promise<void> {
    try {
      const user = await anonymousAuthService.getCurrentUser();
      if (!user) throw new Error('No user found');

      // Get current credits
      const { data: currentData, error: selectError } = await this.supabase
        .from('user_credits')
        .select('total_credits, remaining_credits')
        .eq('user_id', user.id)
        .single();

      if (selectError) throw selectError;

      // Add bonus credits
      const { error: updateError } = await this.supabase
        .from('user_credits')
        .update({
          total_credits: currentData.total_credits + amount,
          remaining_credits: currentData.remaining_credits + amount,
          updated_at: new Date().toISOString()
        })
        .eq('user_id', user.id);

      if (updateError) throw updateError;

      // Create transaction record
      await this.supabase
        .from('credit_transactions')
        .insert({
          user_id: user.id,
          transaction_type: 'bonus',
          amount: amount,
          description: reason
        });

      // Clear cache
      localStorage.removeItem(SupabaseCreditService.CACHE_KEY);

      console.log(`✅ Granted ${amount} bonus credits for: ${reason}`);
    } catch (error) {
      console.error('❌ Failed to grant bonus credits:', error);
      throw error;
    }
  }

  async getTransactionHistory(): Promise<CreditTransaction[]> {
    try {
      const user = await anonymousAuthService.getCurrentUser();
      if (!user) throw new Error('No user found');

      const { data, error } = await this.supabase
        .from('credit_transactions')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })
        .limit(50);

      if (error) throw error;

      return data as CreditTransaction[];
    } catch (error) {
      console.error('❌ Failed to get transaction history:', error);
      return [];
    }
  }
}

// Singleton instance
export const creditService = new SupabaseCreditService();