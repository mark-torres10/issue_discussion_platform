"use client";

import { createContext, use } from "react";
import type { UiCopy } from "@/lib/content/loader";

const UiCopyContext = createContext<UiCopy | null>(null);

interface UiCopyProviderProps {
  copy: UiCopy;
  children: React.ReactNode;
}

/**
 * Provide shared participant UI copy loaded on the server.
 */
export function UiCopyProvider({ copy, children }: UiCopyProviderProps) {
  return <UiCopyContext value={copy}>{children}</UiCopyContext>;
}

/**
 * Read shared UI copy from the nearest provider.
 *
 * Returns
 * -------
 * UiCopy
 *     Shared screen strings from YAML.
 *
 * Raises
 * ------
 * Error
 *     When called outside ``UiCopyProvider``.
 */
export function useUiCopy(): UiCopy {
  const copy = use(UiCopyContext);
  if (!copy) {
    throw new Error("useUiCopy must be used within UiCopyProvider");
  }
  return copy;
}
