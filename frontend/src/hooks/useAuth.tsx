/**
 * useAuth Hook
 *
 * React hook for authentication state and operations.
 */
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import type { User, UserWithToken } from '@/types';
import { api } from '@/lib/api';
import { setTokens, clearAuth, setUser, getUser } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedUser = getUser();
    if (storedUser) {
      setUserState(storedUser as User);
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await api.login({ email, password });
      const userData = response.data as UserWithToken;

      // Store tokens
      setTokens({
        access_token: userData.access_token,
        refresh_token: userData.refresh_token,
        token_type: userData.token_type,
      });

      // Store user
      const { access_token, refresh_token, token_type, ...userWithoutTokens } = userData;
      setUserState(userWithoutTokens);
      setUser(userWithoutTokens as User);

      router.push('/campaigns');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (email: string, password: string, name?: string) => {
    try {
      await api.register({ email, password, name });

      // Auto-login after registration
      await login(email, password);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      clearAuth();
      setUserState(null);
      router.push('/login');
    }
  };

  const refreshUser = async () => {
    try {
      const response = await api.getCurrentUser();
      const userData = response.data;
      setUserState(userData);
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user:', error);
      // If failed, clear auth
      clearAuth();
      setUserState(null);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
