'use client';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { User } from '@supabase/supabase-js';

interface UserMenuProps {
  user: User | null;
  isAnonymous: boolean;
  credits: number;
}

export function UserMenu({ user, isAnonymous, credits }: UserMenuProps) {
  const handleLogout = async () => {
    const response = await fetch('/auth/logout', {
      method: 'POST',
    });

    if (response.redirected) {
      window.location.href = response.url;
    }
  };

  const handleUpgrade = () => {
    window.location.href = '/auth/sign-up';
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger>
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-white relative">
            {isAnonymous ? '👤' : user?.email?.charAt(0).toUpperCase()}
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1">
              {credits}
            </span>
          </div>
        </div>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>
          {isAnonymous ? 'Anonymous User' : user?.email}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isAnonymous ? (
          <DropdownMenuItem onClick={handleUpgrade}>Sign Up Free Account</DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={handleLogout}>Logout</DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}