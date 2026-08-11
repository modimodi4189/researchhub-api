"use client";

import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

type HealthState = "loading" | "connected" | "disconnected";

const statusConfig: Record<
  HealthState,
  {
    label: string;
    dotClassName: string;
    textClassName: string;
  }
> = {
  loading: {
    label: "Loading",
    dotClassName: "bg-muted-foreground",
    textClassName: "text-muted-foreground",
  },
  connected: {
    label: "Connected",
    dotClassName: "bg-primary",
    textClassName: "text-foreground",
  },
  disconnected: {
    label: "Disconnected",
    dotClassName: "bg-destructive",
    textClassName: "text-muted-foreground",
  },
};

export function ApiHealthStatus() {
  const [status, setStatus] = useState<HealthState>("loading");

  useEffect(() => {
    let isCurrent = true;

    async function checkHealth() {
      setStatus("loading");

      try {
        const health = await getHealth();

        if (!isCurrent) {
          return;
        }

        setStatus(health.status === "healthy" ? "connected" : "disconnected");
      } catch {
        if (isCurrent) {
          setStatus("disconnected");
        }
      }
    }

    void checkHealth();

    return () => {
      isCurrent = false;
    };
  }, []);

  const config = statusConfig[status];

  return (
    <div
      className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5"
      aria-live="polite"
      aria-label={`API status: ${config.label}`}
      title="Backend API health"
    >
      <span
        className={`size-2 rounded-full ${config.dotClassName}`}
        aria-hidden="true"
      />
      <span className={`text-xs font-medium ${config.textClassName}`}>
        {config.label}
      </span>
    </div>
  );
}
