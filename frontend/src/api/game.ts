import request from '@/api/request';
import type {
  ForceExitPayload,
  ForceExitResponse,
  GamePreset,
  GameStepResponse,
  NextGamePayload,
  StartGamePayload,
} from '@/types/game';

const LOCAL_PRESETS: GamePreset[] = [
  {
    id: 1,
    title: '普通家庭开局',
    description: '你出生在一个普通家庭，资源有限但关系温暖。',
    worldview: '近未来都市世界，教育和社交依旧是阶层流动的关键。',
    character_options: ['务实内向', '外向冒险', '理性规划'],
    max_attribute_points: 260,
    is_custom: false,
    attributes: [
      { key: 'physique', label: '体质', min_value: 0, max_value: 120, default_value: 0 },
      { key: 'intelligence', label: '智力', min_value: 0, max_value: 120, default_value: 0 },
      { key: 'wealth', label: '家境', min_value: 0, max_value: 120, default_value: 0 },
      { key: 'happiness', label: '幸福', min_value: 0, max_value: 120, default_value: 0 },
    ],
  },
];

const GAME_API_TIMEOUT = 90000;

const shouldRetryGameRequest = (error: unknown): boolean => {
  const normalized = error as { status?: number; message?: string };
  const message = (normalized.message || '').toLowerCase();
  return (
    normalized.status === 0 ||
    normalized.status === 502 ||
    normalized.status === 504 ||
    message.includes('timeout') ||
    message.includes('network')
  );
};

const withOneRetry = async <T>(runner: () => Promise<T>): Promise<T> => {
  try {
    return await runner();
  } catch (error) {
    if (!shouldRetryGameRequest(error)) {
      throw error;
    }
    return runner();
  }
};

export const listPresets = async (): Promise<GamePreset[]> => {
  try {
    const { data } = await request.get<GamePreset[]>('/game/presets');
    if (Array.isArray(data) && data.length > 0) {
      return data;
    }
    return LOCAL_PRESETS;
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status === 404) {
      return LOCAL_PRESETS;
    }
    throw error;
  }
};

export const startGame = async (payload: StartGamePayload): Promise<GameStepResponse> => {
  return withOneRetry(async () => {
    const { data } = await request.post<GameStepResponse>('/game/start', payload, {
      timeout: GAME_API_TIMEOUT,
    });
    return data;
  });
};

export const nextGame = async (payload: NextGamePayload): Promise<GameStepResponse> => {
  return withOneRetry(async () => {
    const { data } = await request.post<GameStepResponse>('/game/next', payload, {
      timeout: GAME_API_TIMEOUT,
    });
    return data;
  });
};

export const forceExitGame = async (payload: ForceExitPayload): Promise<ForceExitResponse> => {
  const { data } = await request.post<ForceExitResponse>('/game/force-exit', payload);
  return data;
};
