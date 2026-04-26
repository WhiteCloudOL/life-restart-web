import axios, {
  AxiosError,
  AxiosHeaders,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
} from 'axios';
import { ACCESS_TOKEN_KEY } from '@/constants/storage';

export interface ToastPayload {
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export interface ApiErrorPayload {
  detail?: string;
  message?: string;
}

export interface ApiError {
  status: number;
  message: string;
}

const REQUEST_TIMEOUT = 15000;

const request = axios.create({
  baseURL: '/api',
  timeout: REQUEST_TIMEOUT,
});

const emitToast = (payload: ToastPayload): void => {
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(
    new CustomEvent<ToastPayload>('app:toast', {
      detail: payload,
    }),
  );
};

const attachToken = (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
  if (typeof window === 'undefined') {
    return config;
  }

  const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  if (!token) {
    return config;
  }

  if (config.headers instanceof AxiosHeaders) {
    config.headers.set('Authorization', `Bearer ${token}`);
    return config;
  }

  const headers = new AxiosHeaders(config.headers);
  headers.set('Authorization', `Bearer ${token}`);
  config.headers = headers;
  return config;
};

const extractErrorMessage = (error: AxiosError<ApiErrorPayload>): string => {
  if (error.code === 'ECONNABORTED' || (error.message || '').toLowerCase().includes('timeout')) {
    return 'AI 响应较慢，请稍后重试（请求超时）';
  }

  const payload = error.response?.data;
  if (payload?.detail) {
    return payload.detail;
  }

  if (payload?.message) {
    return payload.message;
  }

  if (error.message) {
    return error.message;
  }

  return '请求失败，请稍后重试';
};

request.interceptors.request.use(
  (config) => attachToken(config),
  (error) => Promise.reject(error),
);

request.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ApiErrorPayload>) => {
    const statusCode = error.response?.status ?? 0;
    const normalizedError: ApiError = {
      status: statusCode,
      message: extractErrorMessage(error),
    };

    if (typeof window !== 'undefined') {
      if (statusCode === 401) {
        window.localStorage.removeItem(ACCESS_TOKEN_KEY);
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }

      if (statusCode === 429) {
        emitToast({
          type: 'warning',
          message: normalizedError.message || '今日额度已耗尽',
        });
      }
    }

    return Promise.reject(normalizedError);
  },
);

export default request;
