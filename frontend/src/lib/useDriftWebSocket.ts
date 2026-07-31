"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { TerminalLine } from "@/components/Terminal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const MAX_LOG_LINES = 10_000;
const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAY_MS = 2000;

interface DriftWsMessage {
  type: "log" | "phase" | "complete" | "heartbeat" | "error";
  data?: {
    line?: string;
    stream?: "stdout" | "stderr";
    phase?: string;
    message?: string;
    status?: string;
    timestamp?: number;
  };
}

interface UseDriftWebSocketReturn {
  lines: TerminalLine[];
  isConnected: boolean;
  currentPhase: string;
  phaseMessage: string;
  isComplete: boolean;
  error: string | null;
}

function getDriftWsUrl(jobId: string): string {
  const wsBase = API_URL
    .replace("http://", "ws://")
    .replace("https://", "wss://")
    .replace("/api/v1", "");
  return `${wsBase}/ws/drift/${jobId}`;
}

/**
 * Custom hook to connect to the drift WebSocket and accumulate log lines.
 *
 * @param jobId - The drift job ID to subscribe to (null = no connection)
 */
export function useDriftWebSocket(jobId: string | null): UseDriftWebSocketReturn {
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [currentPhase, setCurrentPhase] = useState("init");
  const [phaseMessage, setPhaseMessage] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isCompleteRef = useRef(false);

  // Keep ref in sync
  useEffect(() => {
    isCompleteRef.current = isComplete;
  }, [isComplete]);

  const connect = useCallback((id: string) => {
    if (isCompleteRef.current) return;

    const url = getDriftWsUrl(id);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      reconnectAttemptsRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg: DriftWsMessage = JSON.parse(event.data);

        switch (msg.type) {
          case "log":
            if (msg.data) {
              const newLine: TerminalLine = {
                text: msg.data.line || "",
                stream: msg.data.stream || "stdout",
                phase: msg.data.phase || "init",
                timestamp: msg.data.timestamp || Date.now() / 1000,
              };
              setLines((prev) => {
                const updated = [...prev, newLine];
                // Ring buffer: drop oldest lines if over limit
                if (updated.length > MAX_LOG_LINES) {
                  return updated.slice(updated.length - MAX_LOG_LINES);
                }
                return updated;
              });
            }
            break;

          case "phase":
            if (msg.data?.phase) {
              setCurrentPhase(msg.data.phase);
              if (msg.data.message) {
                setPhaseMessage(msg.data.message);
              }
            }
            break;

          case "complete":
            setIsComplete(true);
            isCompleteRef.current = true;
            if (msg.data?.phase) {
              setCurrentPhase("done");
            }
            break;

          case "error":
            setError(msg.data?.message || "Unknown error");
            break;

          case "heartbeat":
            // Keep-alive, no action needed
            break;
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      wsRef.current = null;

      // Don't reconnect if job is complete or was cleanly closed
      if (isCompleteRef.current || event.code === 1000 || event.code === 1008) {
        return;
      }

      // Attempt reconnection
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++;
        setTimeout(() => {
          if (!isCompleteRef.current) {
            connect(id);
          }
        }, RECONNECT_DELAY_MS);
      } else {
        setError("WebSocket connection lost. Falling back to polling.");
      }
    };

    ws.onerror = () => {
      // Error handling is done in onclose
    };
  }, []);

  useEffect(() => {
    if (!jobId) {
      // Reset state when jobId is cleared
      setLines([]);
      setIsConnected(false);
      setCurrentPhase("init");
      setIsComplete(false);
      setError(null);
      return;
    }

    // Reset for new job
    setLines([]);
    setIsComplete(false);
    setError(null);
    setCurrentPhase("init");
    setPhaseMessage("");
    isCompleteRef.current = false;
    reconnectAttemptsRef.current = 0;

    connect(jobId);

    return () => {
      // Cleanup on unmount or jobId change
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
        wsRef.current = null;
      }
    };
  }, [jobId, connect]);

  return { lines, isConnected, currentPhase, phaseMessage, isComplete, error };
}
