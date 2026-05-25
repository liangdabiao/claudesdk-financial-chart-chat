import { useState, useRef, useCallback, useEffect } from "react";
import type { ChatMessage } from "../types";

export function useWebSocket() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${location.host}/ws`);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "assistant" && msg.message?.role === "assistant") {
        for (const block of msg.message.content) {
          if (block.type === "text" && block.text) {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && !last.toolCall) {
                return [...prev.slice(0, -1), { ...last, content: last.content + block.text }];
              }
              return [...prev, { id: crypto.randomUUID(), role: "assistant", content: block.text }];
            });
            setIsThinking(false);
          }
          if (block.type === "tool_use") {
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                role: "system",
                content: "",
                toolCall: { name: block.name, status: "running", input: block.input },
              },
            ]);
            setIsThinking(true);
          }
        }
      }

      if (msg.type === "tool_result") {
        setMessages((prev) => {
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].toolCall?.status === "running" && prev[i].toolCall?.name) {
              const updated = [...prev];
              updated[i] = { ...updated[i], toolCall: { ...updated[i].toolCall!, status: "done" } };
              return updated;
            }
          }
          return prev;
        });
      }

      if (msg.type === "result") {
        setIsThinking(false);
      }

      if (msg.type === "done") {
        setIsThinking(false);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  const sendMessage = useCallback(
    (content: string, files?: { name: string; path: string }[]) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", content, files },
      ]);
      setIsThinking(true);
      wsRef.current.send(JSON.stringify({ type: "message", content }));
    },
    []
  );

  return { messages, sendMessage, isConnected, isThinking };
}
