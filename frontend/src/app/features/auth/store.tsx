import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from 'react';
import {
  clearStoredAuthToken,
  getStoredAuthToken,
  setUnauthorizedHandler,
  storeAuthToken,
} from '@/lib/api';
import * as authApi from './api';
import type { AuthStatus, AuthUser, LoginRequest, RegisterRequest } from './types';

type AuthState = {
  status: AuthStatus;
  user: AuthUser | null;
  token: string | null;
};

type AuthAction =
  | { type: 'bootstrapStart' }
  | { type: 'authenticated'; user: AuthUser; token: string | null }
  | { type: 'anonymous' }
  | { type: 'logout' };

type AuthContextValue = AuthState & {
  isAuthenticated: boolean;
  isDemoUser: boolean;
  login: (payload: LoginRequest, options?: { remember?: boolean }) => Promise<AuthUser>;
  register: (payload: RegisterRequest, options?: { remember?: boolean }) => Promise<AuthUser>;
  logout: () => Promise<void>;
};

const DEMO_EMAIL = 'demo-student@securehub.local';

const AuthContext = createContext<AuthContextValue | null>(null);

function reducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'bootstrapStart':
      return { ...state, status: 'bootstrapping' };
    case 'authenticated':
      return { status: 'authenticated', user: action.user, token: action.token };
    case 'anonymous':
    case 'logout':
      return { status: 'anonymous', user: null, token: null };
    default:
      return state;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    status: 'bootstrapping',
    user: null,
    token: null,
  });

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearStoredAuthToken();
      dispatch({ type: 'logout' });
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const token = getStoredAuthToken();
    if (!token) {
      dispatch({ type: 'anonymous' });
      return () => {
        cancelled = true;
      };
    }

    dispatch({ type: 'bootstrapStart' });
    authApi
      .me()
      .then((user) => {
        if (!cancelled) {
          dispatch({ type: 'authenticated', user, token });
        }
      })
      .catch(() => {
        clearStoredAuthToken();
        if (!cancelled) {
          dispatch({ type: 'anonymous' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (payload: LoginRequest, options?: { remember?: boolean }) => {
      const response = await authApi.login(payload);
      const remember = options?.remember ?? true;
      storeAuthToken(response.access_token, remember);
      dispatch({
        type: 'authenticated',
        user: response.user,
        token: response.access_token,
      });
      return response.user;
    },
    [],
  );

  const register = useCallback(
    async (payload: RegisterRequest, options?: { remember?: boolean }) => {
      const response = await authApi.register(payload);
      const remember = options?.remember ?? true;
      storeAuthToken(response.access_token, remember);
      dispatch({
        type: 'authenticated',
        user: response.user,
        token: response.access_token,
      });
      return response.user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearStoredAuthToken();
      dispatch({ type: 'logout' });
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      isAuthenticated: state.status === 'authenticated' && !!state.user,
      isDemoUser: state.user?.email === DEMO_EMAIL,
      login,
      register,
      logout,
    }),
    [login, logout, register, state],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return value;
}
