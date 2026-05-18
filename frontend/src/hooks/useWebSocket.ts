import { useState, useEffect, useRef, useCallback } from "react";
import type { HarnessEvent, ConnectionStatus } from "../types/harness";

interface UseWebSocketReturn {
  lastMessage: MessageEvent | null;
  sendMessage: (message: string) => void;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelayBase = 1000;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      setLastMessage(event);
    };

    ws.onclose = (event) => {
      setConnectionStatus("disconnected");
      wsRef.current = null;

      if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = reconnectDelayBase * Math.pow(2, reconnectAttemptsRef.current);
        reconnectAttemptsRef.current++;
        setConnectionStatus("reconnecting");
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      // onclose will fire after this
    };
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  const doReconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    if (wsRef.current) {
      wsRef.current.close(1000, "Manual reconnect");
    }
    connect();
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
      }
    };
  }, [connect]);

  return {
    lastMessage,
    sendMessage,
    connectionStatus,
    reconnect: doReconnect,
  };
}
