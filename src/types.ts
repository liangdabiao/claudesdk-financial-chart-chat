export interface ChartFile {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: ChartFile[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolCall?: {
    name: string;
    status: "running" | "done";
    input?: unknown;
  };
  files?: { name: string; path: string }[];
  images?: string[];
}
