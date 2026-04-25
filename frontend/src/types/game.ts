export interface GamePreset {
  id: number;
  title: string;
  description: string;
  worldview: string;
  character_options: string[];
  max_attribute_points: number;
  is_custom?: boolean;
  attributes: PresetAttributeOption[];
}

export interface PresetAttributeOption {
  key: string;
  label: string;
  min_value: number;
  max_value: number;
  default_value: number;
}

export interface StartGamePayload {
  preset_id: number;
  selected_character_setting?: string | null;
  custom_worldview?: string | null;
  custom_character_setting?: string | null;
  allocated_attributes: Record<string, number>;
  custom_prompt?: string | null;
}

export interface NextGamePayload {
  session_id: number;
  user_choice: string;
}

export interface GameStepResponse {
  session_id: number;
  event: string;
  event_segments: string[];
  current_stats: Record<string, number>;
  is_ended: boolean;
  world_entry_limit: number;
  world_entries_used_today: number;
  model_call_limit: number;
  model_calls_used_today: number;
  next_choices?: string[];
  end_reason?: string | null;
  end_summary?: string | null;
}

export interface ForceExitPayload {
  session_id: number;
}

export interface ForceExitResponse {
  success: boolean;
  end_reason?: string | null;
  end_summary?: string | null;
}

export interface GameHistorySession {
  id: number;
  user_id: number;
  preset_id: number;
  current_stats: Record<string, number>;
  event_history: Array<{
    role: 'system' | 'assistant' | 'user';
    content: string;
    effects?: Record<string, number>;
  }>;
  is_ended: boolean;
}

export interface StoryEvent {
  id: number;
  role: 'system' | 'assistant' | 'user';
  content: string;
}
