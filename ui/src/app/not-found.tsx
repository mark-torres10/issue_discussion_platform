import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            Session not found
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            This study link is invalid. Check the URL from your study invitation
            or open the sample session from the prototype home page.
          </p>
        </div>
        <Link href="/" className={buttonVariants()}>
          Back to prototype home
        </Link>
      </div>
    </AppFrame>
  );
}
