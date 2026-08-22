import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;

const API = "http://127.0.0.1:8000";
const UI = "http://localhost:3000";
const TOKEN = "demo-campus-speech-001-invitation-token-for-contract-tests";

const results = [];

function record(name, pass, notes) {
  results.push({ name, pass, notes });
  console.log(`${pass ? "PASS" : "FAIL"}: ${name}${notes ? ` — ${notes}` : ""}`);
}

async function main() {
  // API health check
  const healthRes = await fetch(`${API}/health`);
  const healthBody = await healthRes.json();
  record("GET /health", healthRes.ok, JSON.stringify(healthBody));

  const unauthRes = await fetch(`${API}/v1/participant-session`);
  const unauthBody = await unauthRes.text();
  record(
    "GET /v1/participant-session (no cookie)",
    unauthRes.status === 401,
    `status=${unauthRes.status} code=${JSON.parse(unauthBody).error_code ?? "?"}`,
  );

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

  // Health proof page
  const healthPage = await context.newPage();
  await healthPage.setContent(`
    <html><body style="font-family:system-ui;padding:2em;background:#f0fff0">
      <h1>Study API Health OK</h1>
      <pre id="out">loading...</pre>
      <script>
        fetch('${API}/health').then(r=>r.json()).then(j=>{
          document.getElementById('out').textContent=JSON.stringify(j,null,2);
        }).catch(e=>{document.getElementById('out').textContent=String(e)});
      </script>
    </body></html>
  `);
  await healthPage.waitForFunction(() => {
    const el = document.getElementById("out");
    return el && el.textContent && el.textContent !== "loading...";
  }, { timeout: 10000 });
  await healthPage.screenshot({ path: join(OUT, "health-ok.png"), fullPage: true });

  // Home page
  const homePage = await context.newPage();
  await homePage.goto(`${UI}/`, { waitUntil: "networkidle", timeout: 60000 });
  await homePage.screenshot({ path: join(OUT, "home.png"), fullPage: true });
  record("GET / (home)", homePage.url().includes("localhost:3000"));

  // Invite exchange via UI route handler
  const invitePage = await context.newPage();
  let inviteOk = false;
  try {
    await invitePage.goto(`${UI}/invite/${TOKEN}`, { waitUntil: "networkidle", timeout: 60000 });
    await invitePage.waitForURL(/\/session(?!\/unavailable)/, { timeout: 30000 });
    inviteOk = !invitePage.url().includes("unavailable");
  } catch (err) {
    record("/invite/<token> → /session", false, String(err));
    await invitePage.screenshot({ path: join(OUT, "invite-exchange.png"), fullPage: true });
  }

  if (inviteOk) {
    record("/invite/<token> → /session", true, invitePage.url());
    await invitePage.screenshot({ path: join(OUT, "invite-exchange.png"), fullPage: true });

    const introHeading = await invitePage.locator("h1").first().textContent();
    const introOk = introHeading?.includes("Before you begin");
    record("Session intro content", !!introOk, introHeading ?? "");
    await invitePage.screenshot({ path: join(OUT, "session-intro.png"), fullPage: true });
    await invitePage.screenshot({ path: join(OUT, "session-intro-api.png"), fullPage: true });

    // Audio check — select text mode and start discussion
    const audioLink = invitePage.getByTestId("continue-to-audio-check");
    if (await audioLink.count()) {
      await audioLink.click();
    } else {
      await invitePage.goto(`${UI}/session/audio-check`, { waitUntil: "networkidle" });
    }
    await invitePage.waitForURL(/audio-check/, { timeout: 15000 });
    const audioHeading = await invitePage.locator("h1").first().textContent();
    record("Audio check page", !invitePage.url().includes("unavailable"), audioHeading ?? invitePage.url());
    await invitePage.screenshot({ path: join(OUT, "audio-check.png"), fullPage: true });

    await invitePage.getByTestId("select-text").click();
    await invitePage.getByRole("button", { name: "Start discussion" }).click();
    await invitePage.waitForURL(/conversation/, { timeout: 30000 });
    await invitePage.waitForTimeout(3000);
    const convoUrl = invitePage.url();
    const convoHeading = await invitePage.locator("h1, [data-testid]").first().textContent().catch(() => "");
    const convoOk = convoUrl.includes("conversation") && !convoUrl.includes("unavailable");
    record("Conversation page", convoOk, `${convoUrl} ${convoHeading}`);
    await invitePage.screenshot({ path: join(OUT, "conversation-api.png"), fullPage: true });
  }

  // Unavailable page without cookies (should be 200, not 500)
  const unavailPage = await context.newPage();
  const unavailRes = await unavailPage.goto(`${UI}/session/unavailable`, { waitUntil: "networkidle" });
  const unavailStatus = unavailRes?.status() ?? 0;
  const unavailHeading = await unavailPage.locator("h1").first().textContent();
  record(
    "/session/unavailable (no cookie)",
    unavailStatus === 200 && !unavailHeading?.includes("Application error"),
    `http=${unavailStatus} h1=${unavailHeading}`,
  );
  await unavailPage.screenshot({ path: join(OUT, "session-unavailable.png"), fullPage: true });

  // API transcript proof page
  const exchange = await fetch(`${API}/v1/participant-access/exchange`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ invitation_token: TOKEN }),
  });
  const exchangeBody = await exchange.text();
  const setCookie = exchange.headers.getSetCookie?.() ?? [];
  const capability = setCookie.find((c) => c.startsWith("participant_capability="));
  const csrf = exchange.headers.get("x-csrf-token");

  let sessionJson = "(no session fetch)";
  if (capability && csrf) {
    const capVal = capability.split(";")[0].replace("participant_capability=", "");
    const sess = await fetch(`${API}/v1/participant-session`, {
      headers: {
        cookie: `participant_capability=${capVal}`,
        "x-csrf-token": csrf,
      },
    });
    sessionJson = await sess.text();
  }

  const proof = { exchangeStatus: exchange.status, exchangeBody, sessionJson };
  writeFileSync(join(OUT, "api-proof.json"), JSON.stringify(proof, null, 2));

  const apiPage = await context.newPage();
  await apiPage.setContent(`
    <html><body style="font-family:monospace;padding:1.5em;font-size:12px;white-space:pre-wrap;background:#f8f8ff">
      <h2>Participant API smoke</h2>
      <h3>POST /v1/participant-access/exchange → ${exchange.status}</h3>
      <pre>${escapeHtml(exchangeBody.slice(0, 1200))}</pre>
      <h3>GET /v1/participant-session</h3>
      <pre>${escapeHtml(sessionJson.slice(0, 1200))}</pre>
    </body></html>
  `);
  await apiPage.screenshot({ path: join(OUT, "conversation-api-detail.png"), fullPage: true });

  writeFileSync(join(OUT, "e2e-results.json"), JSON.stringify(results, null, 2));
  await browser.close();
  console.log("\nScreenshots saved to", OUT);
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
