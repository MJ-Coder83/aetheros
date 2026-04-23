/**
 * WebSocket hook placeholder — for future real-time Tape and simulation updates.
 *
 * When the backend adds a WebSocket endpoint (e.g. ws://localhost:8000/ws),
 * this hook will connect and stream events into the React Query cache.
 *
 * For now it's a no-op stub.
 */

"use client";

import { useEffect, useRef } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

interface UseWebSocketOptions {
  /** Enable the WebSocket connection (default: false while backend has no WS) */
  enabled?: boolean;
  /** Called when a message is received */
  onMessage?: (data: unknown) => void;
}

export function useWebSocket(_options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // WebSocket support is not yet enabled on the backend.
    // Uncomment when the WS endpoint is available:
    //
    // if (!_options.enabled) return;
    //
    // const ws = new WebSocket(WS_URL);
    // wsRef.current = ws;
    //
    // ws.onmessage = (event) => {
    //   try {
    //     const data = JSON.parse(event.data);
    //     _options.onMessage?.(data);
    //   } catch { /* ignore non-JSON */ }
    // };
    //
    // ws.onerror = () => { /* reconnect logic */ };
    // ws.onclose = () => {
    //   setTimeout(() => { /* reconnect */ }, 3000);
    // };
    //
    // return () => {
    //   ws.close();
    //   wsRef.current = null;
    // };

    return undefined;
  }, [_options.enabled, _options.onMessage]);

  return {
    /** Send a message through the WebSocket (when connected). */
    send: (data: unknown) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(data));
      }
    },
    /** Current connection state. */
    readyState: wsRef.current?.readyState ?? WebSocket.CONNECTING,
  };
}
