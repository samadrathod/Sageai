/**
 * useDesktopAgent — connects SAGE web UI to the local Python desktop agent.
 *
 * The Python agent runs on the user's machine at http://localhost:7700.
 * This hook pings the agent on mount and every 10 seconds to check connectivity.
 * When a message looks like a desktop command, it sends it to the agent's
 * /execute endpoint and returns the result without hitting Gemini.
 */
import { useState, useEffect, useRef, useCallback } from "react";

const AGENT_BASE = "http://localhost:7700";
const POLL_INTERVAL = 10_000;

export interface PendingConfirm {
  description: string;
  resolve: (confirmed: boolean) => void;
}

export interface IntentResult {
  handled: boolean;
  response: string;
}

export function useDesktopAgent() {
  const [connected, setConnected] = useState(false);
  const [pendingConfirm, setPendingConfirm] = useState<PendingConfirm | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const ping = useCallback(async () => {
    try {
      const res = await fetch(`${AGENT_BASE}/health`, {
        signal: AbortSignal.timeout(2000),
      });
      setConnected(res.ok);
    } catch {
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    ping();
    pollRef.current = setInterval(ping, POLL_INTERVAL);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [ping]);

  /** Ask user to confirm a destructive action before execution. */
  const requireConfirmation = useCallback((description: string): Promise<boolean> => {
    return new Promise((resolve) => {
      setPendingConfirm({ description, resolve });
    });
  }, []);

  const confirmPending = useCallback(() => {
    if (pendingConfirm) {
      pendingConfirm.resolve(true);
      setPendingConfirm(null);
    }
  }, [pendingConfirm]);

  const dismissPending = useCallback(() => {
    if (pendingConfirm) {
      pendingConfirm.resolve(false);
      setPendingConfirm(null);
    }
  }, [pendingConfirm]);

  /**
   * Send a user message to the agent's /execute endpoint.
   * The agent returns { handled, intent, response, requires_confirm, confirm_description }
   * If requires_confirm is true, we prompt the user before proceeding.
   */
  const executeIntent = useCallback(
    async (message: string): Promise<IntentResult | null> => {
      if (!connected) return null;
      try {
        const res = await fetch(`${AGENT_BASE}/execute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message }),
          signal: AbortSignal.timeout(5000),
        });

        if (!res.ok) return null;
        const data = await res.json();

        // Agent says it doesn't recognise this as a desktop command
        if (!data.handled) return { handled: false, response: "" };

        // Destructive actions need confirmation
        if (data.requires_confirm) {
          const confirmed = await requireConfirmation(data.confirm_description || data.response);
          if (!confirmed) {
            return { handled: true, response: "Action cancelled." };
          }
          // Re-execute with confirmation flag
          const confirmRes = await fetch(`${AGENT_BASE}/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, confirmed: true }),
            signal: AbortSignal.timeout(5000),
          });
          if (!confirmRes.ok) return { handled: true, response: "Agent error during execution." };
          const confirmData = await confirmRes.json();
          return { handled: true, response: confirmData.response };
        }

        return { handled: true, response: data.response };
      } catch {
        return null;
      }
    },
    [connected, requireConfirmation]
  );

  return { connected, executeIntent, pendingConfirm, confirmPending, dismissPending };
}
