import React, { Suspense } from "react";
import CompletePageClient from "./complete-client";

export default function CompletePage() {
  return (
    <Suspense
      fallback={
        <div className="px-5 py-8 text-sm text-muted-foreground">
          Loading completion…
        </div>
      }
    >
      <CompletePageClient />
    </Suspense>
  );
}
