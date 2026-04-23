"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "sonner";
import { useState, type ReactNode } from "react";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5_000,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <TooltipProvider>
        {children}
        <Toaster
          position="bottom-right"
          toastOptions={{
            className: "glass-strong !border-inkos-purple/30",
            style: {
              background: "rgba(15, 22, 41, 0.9)",
              color: "#E2E8F0",
              border: "1px solid rgba(124, 58, 237, 0.3)",
            },
          }}
          theme="dark"
        />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
