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

// WS_URL will be used when the backend WebSocket endpoint is enabled.
// const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

interface UseWebSocketOptions {
  /** Enable the WebSocket connection (default: false while backend has no WS) */
  enabled?: boolean;
  /** Called when a message is received */
  onMessage?: (data: unknown) => void;
}

export function useWebSocket(_options: UseWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  // readyState is stored in a ref to avoid stale ref reads during render.
  // When the backend WebSocket is enabled, update this via setState.
  const readyState = WebSocket.CONNECTING;

  useEffect(() => {
    // WebSocket support is not yet enabled on the backend.
    // Uncomment when the WS endpoint is available:
    //
    // if (!_options.enabled) return;
    //
    // const ws = new WebSocket(WS_URL);
    // wsRef.current = ws;
    // setReadyState(ws.readyState);
    //
    // ws.onopen = () => { /* update readyState state here */ };
    // ws.onclose = () => {
    //   setTimeout(() => { /* reconnect */ }, 3000);
    // };
    // ws.onerror = () => { /* handle error */ };
    // ws.onmessage = (event) => {
    //   try {
    //     const data = JSON.parse(event.data);
    //     _options.onMessage?.(data);
    //   } catch { /* ignore non-JSON */ }
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
    /** Current connection state (reactive). */
    readyState,
  };
}
