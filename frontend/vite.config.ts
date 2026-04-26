import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

// Vite 开发代理：将 /api 请求转发到 FastAPI，避免本地开发跨域问题。
export default defineConfig(({ mode }) => {
  const rootDir = fileURLToPath(new URL('..', import.meta.url));
  const env = {
    ...loadEnv(mode, rootDir, ''),
    ...loadEnv(mode, process.cwd(), ''),
    ...process.env,
  };
  const frontendOrigin = env.FRONTEND_DEV_ORIGIN || 'http://127.0.0.1:5173';
  const frontendUrl = new URL(frontendOrigin);
  const backendHost =
    env.APP_HOST && !['0.0.0.0', '::'].includes(env.APP_HOST) ? env.APP_HOST : '127.0.0.1';
  const backendPort = Number(env.APP_PORT || 8000);
  const devPort = Number(env.VITE_DEV_PORT || frontendUrl.port || 5173);
  const devHost = env.VITE_DEV_HOST || frontendUrl.hostname || '127.0.0.1';
  const apiProxyTarget =
    env.VITE_API_PROXY_TARGET ||
    `http://${backendHost}:${Number.isFinite(backendPort) ? backendPort : 8000}`;
  const allowedHostsRaw = (env.VITE_ALLOWED_HOSTS || '').trim();
  const allowedHosts =
    !allowedHostsRaw || allowedHostsRaw === '*'
      ? true
      : allowedHostsRaw
          .split(',')
          .map((host) => host.trim())
          .filter(Boolean);

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: devHost,
      port: Number.isFinite(devPort) ? devPort : 5173,
      allowedHosts,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
