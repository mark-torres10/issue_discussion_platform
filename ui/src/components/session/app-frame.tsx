import { cn } from "@/lib/utils";

interface AppFrameProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Narrow centered frame used by all participant screens.
 */
export function AppFrame({ children, className }: AppFrameProps) {
  return (
    <div className="flex flex-1 justify-center px-4 py-6 sm:px-6 sm:py-10">
      <div
        className={cn(
          "flex w-full max-w-xl flex-col rounded-2xl bg-white shadow-[0_1px_0_rgba(40,30,20,0.04)] ring-1 ring-black/5",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}
