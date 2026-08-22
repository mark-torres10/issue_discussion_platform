import { chromium } from "playwright";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const UI = "http://localhost:3000";
const TOKEN = "demo-campus-speech-001-invitation-token-for-contract-tests";

async function main() {
  const browser = await chromium.launch({
    headless: false,
    args: ["--start-maximized"],
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  await page.goto(`${UI}/invite/${TOKEN}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  await page.getByTestId("continue-to-audio-check").click();
  await page.waitForURL(/audio-check/);
  await page.waitForTimeout(2000);

  await page.getByTestId("select-text").click();
  await page.waitForTimeout(1000);
  await page.getByRole("button", { name: "Start discussion" }).click();
  await page.waitForURL(/conversation/);
  await page.waitForTimeout(4000);

  await browser.close();
}

main().catch(console.error);
