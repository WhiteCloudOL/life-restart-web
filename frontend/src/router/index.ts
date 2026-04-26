import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { pinia } from '@/stores';

const LoginView = () => import('@/views/Login.vue');
const RegisterView = () => import('@/views/Register.vue');
const HomeView = () => import('@/views/Home.vue');
const GameSessionView = () => import('@/views/GamePlay.vue');
const ProfileView = () => import('@/views/Profile.vue');
const AdminView = () => import('@/views/Admin.vue');
const NotFoundView = () => import('@/views/NotFound.vue');

const MainLayout = () => import('@/layouts/MainLayout.vue');
const AuthLayout = () => import('@/layouts/AuthLayout.vue');

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView,
          meta: {
            title: '大厅',
            requiresAuth: true,
          },
        },
        {
          path: 'game',
          name: 'game-session',
          component: GameSessionView,
          meta: {
            title: '推演中',
            requiresAuth: true,
          },
        },
        {
          path: 'profile',
          name: 'profile',
          component: ProfileView,
          meta: {
            title: '个人设置',
            requiresAuth: true,
          },
        },
        {
          path: 'admin',
          name: 'admin',
          component: AdminView,
          meta: {
            title: '管理员看板',
            requiresAuth: true,
            requiresAdmin: true,
          },
        },
      ],
    },
    {
      path: '/',
      component: AuthLayout,
      children: [
        {
          path: 'login',
          name: 'login',
          component: LoginView,
          meta: {
            title: '登录',
            guestOnly: true,
          },
        },
        {
          path: 'register',
          name: 'register',
          component: RegisterView,
          meta: {
            title: '注册',
            guestOnly: true,
          },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView,
      meta: {
        title: '页面不存在',
      },
    },
  ],
});

const ensureUserLoaded = async (): Promise<void> => {
  const authStore = useAuthStore(pinia);
  if (!authStore.token || authStore.user || authStore.isFetchingUser) {
    return;
  }

  await authStore.fetchUserInfo();
};

const resolveAuthRedirect = (to: RouteLocationNormalized): string | null => {
  const authStore = useAuthStore(pinia);
  const isLoggedIn = Boolean(authStore.token);

  if (to.meta.requiresAuth && !isLoggedIn) {
    return '/login';
  }

  if (to.meta.guestOnly && isLoggedIn) {
    return '/';
  }

  if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    return '/';
  }

  return null;
};

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);

  // 进入需要鉴权页面前尝试拉取用户信息，避免刷新后 user 丢失导致权限误判。
  if ((to.meta.requiresAuth || to.meta.requiresAdmin) && authStore.token) {
    try {
      await ensureUserLoaded();
    } catch {
      return '/login';
    }
  }

  const redirectPath = resolveAuthRedirect(to);
  if (redirectPath) {
    if (redirectPath === '/login') {
      return {
        path: '/login',
        query: {
          redirect: to.fullPath,
        },
      };
    }
    return redirectPath;
  }

  return true;
});

router.afterEach((to) => {
  const appName = 'AI 人生重开模拟器';
  const pageTitle = to.meta.title ? `${to.meta.title} | ${appName}` : appName;
  document.title = pageTitle;
});

export default router;
