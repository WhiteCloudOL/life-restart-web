<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { createAdminUser, deleteAdminUser, listUsersByPage, updateAdminUser } from '@/api/admin';
import BaseButton from '@/components/BaseButton.vue';
import BaseModal from '@/components/BaseModal.vue';
import { useAuthStore } from '@/stores/useAuthStore';
import type { AdminUser, CreateAdminUserPayload, UpdateAdminUserPayload } from '@/types/admin';

type DialogMode = 'create' | 'edit';

const users = ref<AdminUser[]>([]);
const authStore = useAuthStore();
const page = ref<number>(1);
const size = 10;
const total = ref<number>(0);
const isLoading = ref<boolean>(false);
const errorMessage = ref<string>('');
const isSubmitting = ref<boolean>(false);
const deletingUserId = ref<number | null>(null);

const dialogVisible = ref<boolean>(false);
const dialogMode = ref<DialogMode>('edit');
const editingUser = ref<AdminUser | null>(null);

const formUsername = ref<string>('');
const formNickname = ref<string>('');
const formPassword = ref<string>('');
const formIsAdmin = ref<boolean>(false);
const formWorldEntryLimit = ref<string>('0');
const formModelCallLimit = ref<string>('0');
const formModelCallsUsedToday = ref<string>('0');

const totalPages = computed<number>(() => Math.max(Math.ceil(total.value / size), 1));
const dialogTitle = computed<string>(() =>
  dialogMode.value === 'create' ? '新增账户' : '编辑用户',
);

const toast = (type: 'success' | 'warning' | 'error', message: string): void => {
  window.dispatchEvent(new CustomEvent('app:toast', { detail: { type, message } }));
};

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

const resetForm = (): void => {
  formUsername.value = '';
  formNickname.value = '';
  formPassword.value = '';
  formIsAdmin.value = false;
  formWorldEntryLimit.value = '0';
  formModelCallLimit.value = '0';
  formModelCallsUsedToday.value = '0';
};

const closeDialog = (): void => {
  dialogVisible.value = false;
  editingUser.value = null;
  resetForm();
};

const openCreateDialog = (): void => {
  dialogMode.value = 'create';
  editingUser.value = null;
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (user: AdminUser): void => {
  dialogMode.value = 'edit';
  editingUser.value = user;
  formUsername.value = user.username;
  formNickname.value = user.nickname;
  formPassword.value = '';
  formIsAdmin.value = user.is_admin;
  formWorldEntryLimit.value = String(user.world_entry_limit);
  formModelCallLimit.value = String(user.model_call_limit);
  formModelCallsUsedToday.value = String(user.model_calls_used_today);
  dialogVisible.value = true;
};

const parseNonNegativeInteger = (value: string, label: string): number => {
  const nextValue = Number(value);
  if (!Number.isInteger(nextValue) || nextValue < 0) {
    throw new Error(`${label}必须是大于等于 0 的整数`);
  }
  return nextValue;
};

const syncCurrentUserIfNeeded = (updated: AdminUser): void => {
  if (updated.id !== authStore.user?.user_id) {
    return;
  }
  authStore.syncAdminManagedProfile(
    updated.nickname,
    updated.is_admin,
    updated.world_entry_limit,
    updated.world_entries_used_today,
    updated.model_call_limit,
    updated.model_calls_used_today,
  );
};

const submitDialog = async (): Promise<void> => {
  try {
    const nickname = formNickname.value.trim();
    const worldEntryLimit = parseNonNegativeInteger(formWorldEntryLimit.value, '每日进入次数');
    const modelCallLimit = parseNonNegativeInteger(formModelCallLimit.value, '模型调用上限');
    const modelCallsUsedToday = parseNonNegativeInteger(
      formModelCallsUsedToday.value,
      '模型调用已用次数',
    );
    if (modelCallsUsedToday > modelCallLimit) {
      throw new Error('模型调用已用次数不能超过模型调用上限');
    }

    isSubmitting.value = true;
    if (dialogMode.value === 'create') {
      const username = formUsername.value.trim();
      const password = formPassword.value;
      if (!username) {
        throw new Error('请输入用户名');
      }
      if (!password) {
        throw new Error('请输入密码');
      }
      const payload: CreateAdminUserPayload = {
        username,
        password,
        nickname: nickname || undefined,
        is_admin: formIsAdmin.value,
      };
      await createAdminUser(payload);
      toast('success', '账户已创建');
      closeDialog();
      page.value = 1;
      await loadPage();
      return;
    }

    if (!editingUser.value) {
      return;
    }
    const payload: UpdateAdminUserPayload = {
      nickname: nickname || undefined,
      is_admin: formIsAdmin.value,
      world_entry_limit: worldEntryLimit,
      model_call_limit: modelCallLimit,
      model_calls_used_today: modelCallsUsedToday,
    };
    if (formPassword.value.trim()) {
      payload.password = formPassword.value;
    }
    const updated = await updateAdminUser(editingUser.value.id, payload);
    users.value = users.value.map((item) => (item.id === updated.id ? updated : item));
    syncCurrentUserIfNeeded(updated);
    toast('success', '用户信息已更新');
    closeDialog();
  } catch (error) {
    const message = (error as { message?: string }).message ?? '操作失败';
    toast('error', message);
  } finally {
    isSubmitting.value = false;
  }
};

const removeUser = async (user: AdminUser): Promise<void> => {
  const confirmed = window.confirm(`确认删除账户 ${user.username} 吗？该用户的历史游戏记录也会被删除。`);
  if (!confirmed) {
    return;
  }
  deletingUserId.value = user.id;
  try {
    await deleteAdminUser(user.id);
    users.value = users.value.filter((item) => item.id !== user.id);
    total.value = Math.max(0, total.value - 1);
    toast('success', '账户已删除');
    if (users.value.length === 0 && page.value > 1) {
      page.value -= 1;
      await loadPage();
    }
  } catch (error) {
    const message = (error as { message?: string }).message ?? '删除失败';
    toast('error', message);
  } finally {
    deletingUserId.value = null;
  }
};

onMounted(loadPage);
</script>

<template>
  <section class="panel">
    <header class="head">
      <div>
        <h1>管理员看板</h1>
        <p>集中管理账户、角色、昵称、密码，以及每日次数与模型调用用量</p>
      </div>
      <BaseButton type="button" :block="false" @click="openCreateDialog">新增账户</BaseButton>
    </header>

    <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    <p v-if="isLoading" class="hint">加载中...</p>

    <div v-if="!isLoading" class="table-wrap">
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
              <div class="row-actions">
                <button class="link-btn" type="button" @click="openEditDialog(user)">编辑</button>
                <button
                  class="link-btn danger-btn"
                  type="button"
                  :disabled="deletingUserId === user.id"
                  @click="removeUser(user)"
                >
                  {{ deletingUserId === user.id ? '删除中...' : '删除' }}
                </button>
              </div>
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

  <BaseModal :visible="dialogVisible" :title="dialogTitle" @close="closeDialog">
    <form class="user-form" @submit.prevent="submitDialog">
      <label v-if="dialogMode === 'create'">
        <span>用户名</span>
        <input v-model="formUsername" type="text" maxlength="32" autocomplete="off" />
      </label>
      <label>
        <span>昵称</span>
        <input v-model="formNickname" type="text" maxlength="32" autocomplete="off" />
      </label>
      <label>
        <span>{{ dialogMode === 'create' ? '密码' : '新密码（留空则不修改）' }}</span>
        <input
          v-model="formPassword"
          type="password"
          maxlength="128"
          :autocomplete="dialogMode === 'create' ? 'new-password' : 'off'"
        />
      </label>
      <label>
        <span>角色</span>
        <select v-model="formIsAdmin">
          <option :value="false">普通用户</option>
          <option :value="true">管理员</option>
        </select>
      </label>
      <template v-if="dialogMode === 'edit'">
        <label>
          <span>每日进入次数</span>
          <input v-model="formWorldEntryLimit" type="number" min="0" step="1" />
        </label>
        <label>
          <span>模型调用上限</span>
          <input v-model="formModelCallLimit" type="number" min="0" step="1" />
        </label>
        <label>
          <span>模型调用已用次数</span>
          <input v-model="formModelCallsUsedToday" type="number" min="0" step="1" />
        </label>
      </template>
      <div class="actions">
        <button type="button" class="ghost" @click="closeDialog">取消</button>
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

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
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

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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

.danger-btn {
  color: var(--danger);
}

.danger-btn:hover {
  background: rgba(255, 230, 230, 0.9);
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

.user-form {
  display: grid;
  gap: 12px;
}

.user-form label {
  display: grid;
  gap: 6px;
}

.user-form span {
  color: var(--subtext);
  font-size: 13px;
}

.user-form input,
.user-form select {
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

@media (max-width: 720px) {
  .head {
    flex-direction: column;
    align-items: stretch;
  }

  .row-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
