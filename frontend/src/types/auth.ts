export interface AuthTokenResponse {
  access_token: string;
  token_type: 'bearer' | string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
}
