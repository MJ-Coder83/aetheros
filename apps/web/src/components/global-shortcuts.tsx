"use client";

import { useKeyboardShortcuts } from "@/hooks/use-keyboard-shortcuts";

/** Mounts global keyboard shortcut listeners. */
export function GlobalShortcuts() {
  useKeyboardShortcuts();
  return null;
}
