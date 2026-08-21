'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { getUser, isAuthenticated, setTokens, setUser, clearAuth, type StoredUser } from '@/lib/auth';

interface UseAuthReturn {
  isAuthenticated: boolean;
  user: StoredUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const router = useRouter();
  const [state, setState] = useState<{
    isAuthenticated: boolean;
    user: StoredUser | null;
    isLoading: boolean;
  }>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
  });

  // Check auth on mount
  useEffect(() => {
    const checkAuth = () => {
      try {
        const authenticated = isAuthenticated();
        const user = getUser();

        setState({
          isAuthenticated: authenticated,
          user,
          isLoading: false,
        });
      } catch (error) {
        console.error('Auth check failed:', error);
        setState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
        });
      }
    };

    checkAuth();
  }, []);

  // Login function
  const login = useCallback(async (email: string, password: string) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const response = await api.login({ email, password });
      const data = response.data;

      // Backend returns: { id, email, name, role, ..., access_token, refresh_token, token_type }
      const { access_token, refresh_token, token_type } = data;

      // Store tokens
      setTokens({
        access_token,
        refresh_token,
        token_type,
      });

      // Store user from login response (no need for extra API call)
      const userData = {
        id: data.id,
        email: data.email,
        name: data.name,
        role: data.role,
      };
      setUser(userData);

      setState({
        isAuthenticated: true,
        user: userData,
        isLoading: false,
      });

      // Redirect to campaigns
      router.push('/campaigns');
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, [router]);

  // Register function
  const register = useCallback(async (email: string, password: string, name?: string) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      // Register the user (returns UserResponse without tokens)
      await api.register({ email, password, name });

      // After successful registration, login to get tokens
      const loginResponse = await api.login({ email, password });
      const data = loginResponse.data;

      // Backend returns: { id, email, name, role, ..., access_token, refresh_token, token_type }
      const { access_token, refresh_token, token_type } = data;

      // Store tokens
      setTokens({
        access_token,
        refresh_token,
        token_type,
      });

      // Store user from login response (no need for extra API call)
      const userData = {
        id: data.id,
        email: data.email,
        name: data.name,
        role: data.role,
      };
      setUser(userData);

      setState({
        isAuthenticated: true,
        user: userData,
        isLoading: false,
      });

      // Redirect to campaigns
      router.push('/campaigns');
    } catch (error) {
      setState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, [router]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
      setState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
      router.push('/login');
    }
  }, [router]);

  return {
    ...state,
    login,
    register,
    logout,
  };
}
