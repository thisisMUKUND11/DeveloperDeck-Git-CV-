"use client";

import { useEffect } from "react";

import { recordView } from "@/lib/api";

/** Fires one view increment per browser open of a shared link. Runs only in
 *  the browser, so server prefetch and OG-image generation don't inflate it. */
export function ViewBeacon({ token }: { token: string }) {
  useEffect(() => {
    recordView(token);
  }, [token]);
  return null;
}
