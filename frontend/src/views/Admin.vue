<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { listUsersByPage, updateUserQuota } from '@/api/admin';
import BaseButton from '@/components/BaseButton.vue';
import BaseModal from '@/components/BaseModal.vue';
import { useAuthStore } from '@/stores/useAuthStore';
import type { AdminUser } from '@/types/admin';

const users = ref<AdminUser[]>([]);
const authStore = useAuthStore();
const page = ref<number>(1);
const size = 10;
const total = ref<number>(0);
const isLoading = ref<boolean>(false);
const errorMessage = ref<string>('');

const editingUser = ref<AdminUser | null>(null);
const editingWorldEntryLimit = ref<string>('0');
const editingModelCallLimit = ref<string>('0');
const isSubmitting = ref<boolean>(false);

const totalPages = computed<number>(() => Math.max(Math.ceil(total.value / size), 1));

const loadPage = async (): Promise<void> => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const resp = await listUsersByPage(page.value, size);
    users.value = resp.items;
    total.value = resp.total;
  } catch (error) {
    const message = (error as { message?: string }).message;
    errorMessage.value = message ?? '加载失败';
  } finally {
    isLoading.value = false;
  }
};

const openQuotaDialog = (user: AdminUser): void => {
  editingUser.value = user;
  editingWorldEntryLimit.value = String(user.world_entry_limit);
  editingModelCallLimit.value = String(user.model_call_limit);
};

const closeQuotaDialog = (): void => {
  editingUser.value = null;
};

const submitQuota = async (): Promise<void> => {
  if (!editingUser.value) {
    return;
  }
  const nextWorldEntry = Number(editingWorldEntryLimit.value);
  const nextModelCalls = Number(editingModelCallLimit.value);
  if (
    !Number.isFinite(nextWorldEntry) ||
    !Number.isFinite(nextModelCalls) ||
    nextWorldEntry < 0 ||
    nextModelCalls < 0
  ) {
    window.dispatchEvent(
      new CustomEvent('app:toast', {
        detail: { type: 'warning', message: '请输入正确的次数（>= 0）' },
      }),
    );
    return;
  }

  isSubmitting.value = true;
  try {
    const updated = await updateUserQuota(editingUser.value.id, {
      world_entry_limit: nextWorldEntry,
      model_call_limit: nextModelCalls,
    });
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item));
    if (updated.id === authStore.user?.user_id) {
      authStore.syncQuota(
        updated.world_entry_limit,
        updated.world_entries_used_today,
        updated.model_call_limit,
        updated.model_calls_used_today,
      );
    }
    closeQuotaDialog();
  } catch (error) {
    const message = (error as { message?: string }).message ?? '更新失败';
    window.dispatchEvent(
      new CustomEvent('app:toast', {
        detail: { type: 'error', message },
      }),
    );
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(loadPage);
</script>

<template>
  <section class="panel">
    <header class="head">
      <h1>管理员看板</h1>
      <p>管理每个用户的每日进入次数与可用模型调用次数</p>
    </header>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="hint">加载中...</p>

    <div class="table-wrap" v-if="!isLoading">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>昵称</th>
            <th>角色</th>
            <th>API模式</th>
            <th>每日进入次数</th>
            <th>已用</th>
            <th>模型调用上限</th>
            <th>模型调用已用</th>
            <th>自定义API</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.nickname }}</td>
            <td>{{ user.is_admin ? '管理员' : '普通用户' }}</td>
            <td>{{ user.api_mode === 'custom' ? '自定义API' : '默认API' }}</td>
            <td>{{ user.world_entry_limit }}</td>
            <td>{{ user.world_entries_used_today }}</td>
            <td>{{ user.model_call_limit }}</td>
            <td>{{ user.model_calls_used_today }}</td>
            <td>{{ user.has_custom_api_key ? '是' : '否' }}</td>
            <td>
              <button class="link-btn" type="button" @click="openQuotaDialog(user)">修改次数</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pager">
      <button type="button" :disabled="page <= 1" @click="page -= 1; loadPage()">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button type="button" :disabled="page >= totalPages" @click="page += 1; loadPage()">下一页</button>
    </footer>
  </section>

  <BaseModal :visible="Boolean(editingUser)" title="调整用户额度" @close="closeQuotaDialog">
    <form class="quota-form" @submit.prevent="submitQuota">
      <p v-if="editingUser">用户：{{ editingUser.username }}（ID: {{ editingUser.id }}）</p>
      <label>
        <span>每日进入次数</span>
        <input v-model="editingWorldEntryLimit" type="number" min="0" step="1" />
      </label>
      <label>
        <span>模型调用上限</span>
        <input v-model="editingModelCallLimit" type="number" min="0" step="1" />
      </label>
      <div class="actions">
        <button type="button" class="ghost" @click="closeQuotaDialog">取消</button>
        <BaseButton type="submit" :loading="isSubmitting">保存</BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<style scoped>
.panel {
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--panel);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-soft);
}

.head h1 {
  margin: 0;
  color: var(--title);
  font-family: var(--font-serif);
}

.head p {
  margin: 10px 0 0;
  color: var(--subtext);
}

.error {
  color: var(--danger);
}

.hint {
  color: var(--subtext);
}

.table-wrap {
  overflow: auto;
  margin-top: 16px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.66);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  border-bottom: 1px solid var(--line);
  padding: 10px 8px;
  white-space: nowrap;
  color: var(--text);
}

th {
  color: var(--subtext);
  font-size: 13px;
}

.link-btn {
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
  color: var(--accent);
  border-radius: 999px;
  padding: 4px 10px;
  cursor: pointer;
  transition: transform 0.3s ease, background-color 0.3s ease;
}

.link-btn:hover {
  transform: translateY(-1px) scale(1.02);
  background: rgba(222, 247, 239, 0.9);
}

.pager {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
}

.pager button {
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
  color: var(--text);
  border-radius: 8px;
  height: 32px;
  padding: 0 12px;
}

.quota-form {
  display: grid;
  gap: 12px;
}

.quota-form label {
  display: grid;
  gap: 6px;
}

.quota-form span {
  color: var(--subtext);
  font-size: 13px;
}

.quota-form input {
  height: 40px;
  border-radius: 8px;
  border: 1px solid var(--line);
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.95);
  color: var(--text);
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.ghost {
  height: 42px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
  color: var(--text);
}
</style>
