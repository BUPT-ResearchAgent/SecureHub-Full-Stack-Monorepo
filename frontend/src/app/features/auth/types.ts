export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  password: string;
  display_name: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: 'bearer';
  expires_at: string;
  user: AuthUser;
};

export type AuthStatus = 'bootstrapping' | 'anonymous' | 'authenticated';
