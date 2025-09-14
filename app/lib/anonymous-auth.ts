'use client';

import { createClient } from '@/lib/supabase/client';
import { User } from '@supabase/supabase-js';

export interface AnonymousAuthService {
  initializeAnonymousUser(): Promise<User>;
  upgradeToRegistered(email: string, password: string): Promise<User>;
  getCurrentUser(): Promise<User | null>;
  isAnonymous(): Promise<boolean>;
  getOrCreateAnonymousSession(): Promise<User>;
}

export class SupabaseAnonymousAuthService implements AnonymousAuthService {
  private supabase = createClient();

  async initializeAnonymousUser(): Promise<User> {
    try {
      const { data, error } = await this.supabase.auth.signInAnonymously();
      if (error) throw error;
      
      console.log('✅ Anonymous user created:', data.user?.id);
      return data.user!;
    } catch (error) {
      console.error('❌ Failed to create anonymous user:', error);
      throw error;
    }
  }

  async upgradeToRegistered(email: string, password: string): Promise<User> {
    try {
      // Update the current anonymous user with email and password
      const { data, error } = await this.supabase.auth.updateUser({
        email,
        password
      });
      
      if (error) throw error;
      
      console.log('✅ Anonymous user upgraded to registered:', data.user.id);
      return data.user!;
    } catch (error) {
      console.error('❌ Failed to upgrade anonymous user:', error);
      throw error;
    }
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const { data: { user } } = await this.supabase.auth.getUser();
      return user;
    } catch (error) {
      console.error('❌ Failed to get current user:', error);
      return null;
    }
  }

  async isAnonymous(): Promise<boolean> {
    try {
      const user = await this.getCurrentUser();
      return user?.is_anonymous || !user?.email;
    } catch (error) {
      console.error('❌ Failed to check if user is anonymous:', error);
      return false;
    }
  }

  async getOrCreateAnonymousSession(): Promise<User> {
    try {
      let user = await this.getCurrentUser();
      
      if (!user) {
        user = await this.initializeAnonymousUser();
      }
      
      return user;
    } catch (error) {
      console.error('❌ Failed to get or create anonymous session:', error);
      throw error;
    }
  }
}

// Singleton instance
export const anonymousAuthService = new SupabaseAnonymousAuthService();