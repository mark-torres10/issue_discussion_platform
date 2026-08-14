import Link from "next/link";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SAMPLE_SESSION_ID } from "@/lib/api/study-backend";
import { loadUiCopy } from "@/lib/content/loader";
import { UiCopyProvider } from "@/lib/content/content-provider";
import type { Metadata } from "next";
import "./globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source-sans",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const copy = loadUiCopy();
  return {
    title: copy.metadata.title,
    description: copy.metadata.description,
  };
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  const copy = loadUiCopy();

  return (
    <html
      lang="en"
      className={`${sourceSans.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-[var(--page-bg)] font-sans text-[var(--ink)]">
        <UiCopyProvider copy={copy}>
          <TooltipProvider>
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
            >
              {copy.layout.skipToContent}
            </a>
            <header className="px-4 py-3 text-center text-xs text-muted-foreground">
              <Link href="/" className="hover:text-[var(--ink)]">
                {copy.layout.headerBrand}
              </Link>
              <span className="mx-2" aria-hidden="true">
                ·
              </span>
              <Link
                href={`/session/${SAMPLE_SESSION_ID}`}
                className="hover:text-[var(--ink)]"
              >
                {copy.layout.openSampleSession}
              </Link>
            </header>
            <main id="main-content" className="flex flex-1 flex-col">
              {children}
            </main>
          </TooltipProvider>
        </UiCopyProvider>
      </body>
    </html>
  );
}
