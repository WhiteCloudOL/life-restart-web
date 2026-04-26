import { createApp } from 'vue';
import App from '@/App.vue';
import router from '@/router';
import { pinia } from '@/stores';
import '@/assets/main.css';

const app = createApp(App);

if (typeof window !== 'undefined') {
  window.addEventListener('auth:unauthorized', () => {
    const isOnLoginPage = window.location.pathname === '/login';
    if (isOnLoginPage) {
      return;
    }

    void router.replace({
      path: '/login',
      query: {
        redirect: `${window.location.pathname}${window.location.search}`,
      },
    });
  });
}

app.use(pinia);
app.use(router);

app.mount('#app');
