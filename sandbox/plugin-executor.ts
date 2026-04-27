#!/usr/bin/env -S deno run --allow-net --allow-read --allow-write=/tmp/sandbox --timeout=30000
/**
 * Plugin Sandbox Executor
 *
 * Runs plugins in a restricted Deno environment.
 * Plugins are loaded as ES modules with controlled permissions.
 */

import type { PluginManifest } from "./types.ts";

interface PluginContext {
  pluginId: string;
  entryPoint: string;
  permissions: string[];
  input: Record<string, unknown>;
}

interface PluginResult {
  success: boolean;
  result?: unknown;
  error?: string;
}

// Restricted fetch that checks whitelist
async function restrictedFetch(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const allowedHosts = Deno.env.get("ALLOWED_HOSTS")?.split(",") ?? [];
  const parsed = new URL(url);

  if (!allowedHosts.includes(parsed.hostname)) {
    throw new Error(`Network access to ${parsed.hostname} not allowed`);
  }

  return await fetch(url, init);
}

// Restricted filesystem operations
const restrictedFS = {
  readFile: async (path: string): Promise<Uint8Array> => {
    if (!path.startsWith("/tmp/sandbox/")) {
      throw new Error(`File access outside sandbox not allowed: ${path}`);
    }
    return await Deno.readFile(path);
  },
  writeFile: async (path: string, data: Uint8Array): Promise<void> => {
    if (!path.startsWith("/tmp/sandbox/")) {
      throw new Error(`File write outside sandbox not allowed: ${path}`);
    }
    await Deno.writeFile(path, data);
  },
  readTextFile: async (path: string): Promise<string> => {
    if (!path.startsWith("/tmp/sandbox/")) {
      throw new Error(`File access outside sandbox not allowed: ${path}`);
    }
    return await Deno.readTextFile(path);
  },
  writeTextFile: async (path: string, data: string): Promise<void> => {
    if (!path.startsWith("/tmp/sandbox/")) {
      throw new Error(`File write outside sandbox not allowed: ${path}`);
    }
    await Deno.writeTextFile(path, data);
  },
};

// Plugin execution
async function executePlugin(context: PluginContext): Promise<PluginResult> {
  const { entryPoint, input } = context;

  try {
    // Import plugin as module with restricted capabilities
    const pluginModule = await import(entryPoint);

    // Validate export
    if (typeof pluginModule.run !== "function") {
      throw new Error("Plugin must export a 'run' function");
    }

    // Execute plugin with sandboxed context
    const sandbox = {
      input,
      fetch: restrictedFetch,
      fs: restrictedFS,
      console: {
        log: (...args: unknown[]) => {
          Deno.stdout.write(
            new TextEncoder().encode(
              JSON.stringify({ level: "info", args }) + "\n",
            ),
          );
        },
        error: (...args: unknown[]) => {
          Deno.stderr.write(
            new TextEncoder().encode(
              JSON.stringify({ level: "error", args }) + "\n",
            ),
          );
        },
      },
    };

    const result = await pluginModule.run(sandbox);

    return { success: true, result };
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return { success: false, error: errorMessage };
  }
}

// Main entry
if (import.meta.main) {
  // Read context from stdin
  const decoder = new TextDecoder();
  const input = await Deno.stdin.read(new Uint8Array(65536));
  const stdin = input ? decoder.decode(input) : "";

  try {
    const context: PluginContext = JSON.parse(stdin);
    const result = await executePlugin(context);
    const encoder = new TextEncoder();
    await Deno.stdout.write(encoder.encode(JSON.stringify(result) + "\n"));
    Deno.exit(result.success ? 0 : 1);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    const encoder = new TextEncoder();
    await Deno.stdout.write(
      encoder.encode(JSON.stringify({ success: false, error: msg }) + "\n"),
    );
    Deno.exit(1);
  }
}
