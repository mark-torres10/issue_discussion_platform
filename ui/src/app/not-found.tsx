import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";
import { loadUiCopy } from "@/lib/content/loader";

export default function NotFound() {
  const copy = loadUiCopy();

  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {copy.notFound.heading}
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {copy.notFound.body}
          </p>
        </div>
        <Link href="/" className={buttonVariants()}>
          {copy.notFound.backHome}
        </Link>
      </div>
    </AppFrame>
  );
}
