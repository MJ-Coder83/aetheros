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
            className: "glass-strong !border-inkos-cyan/15",
            style: {
              background: "rgba(15, 22, 41, 0.85)",
              color: "#E8ECF4",
              border: "1px solid rgba(34, 211, 238, 0.12)",
            },
          }}
          theme="dark"
        />
      </TooltipProvider>
    </QueryClientProvider>
  );
}
