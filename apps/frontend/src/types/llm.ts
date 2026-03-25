export type LlmStatusResponse = {
  enabled: boolean;
  provider: string;
  ollama_base_url: string;
  chat_model: string;
  embed_model: string;
  timeout_seconds: number;
  reachable: boolean;
  status: string;
  message: string;
};
