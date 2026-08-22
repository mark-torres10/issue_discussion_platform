import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;

const API = "http://127.0.0.1:8000";
const UI = "http://127.0.0.1:3000";
const TOKEN = "demo-campus-speech-001-invitation-token-for-contract-tests";

async function main() {
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

  // Invite exchange via UI (sets cookies server-side)
  const invitePage = await context.newPage();
  await invitePage.goto(`${UI}/invite/${TOKEN}`, { waitUntil: "networkidle", timeout: 60000 });
  await invitePage.waitForURL(/\/session/, { timeout: 30000 });
  await invitePage.screenshot({ path: join(OUT, "invite-exchange.png"), fullPage: true });

  // Session introduction page
  const sessionPage = invitePage;
  await sessionPage.waitForTimeout(1000);
  await sessionPage.screenshot({ path: join(OUT, "session-intro.png"), fullPage: true });

  // Conversation page (may redirect if session not started)
  const convoPage = await context.newPage();
  await convoPage.goto(`${UI}/session/conversation`, { waitUntil: "networkidle", timeout: 60000 });
  await convoPage.waitForTimeout(1500);
  await convoPage.screenshot({ path: join(OUT, "conversation-api.png"), fullPage: true });

  // API transcript via curl-equivalent in page for proof
  const apiPage = await context.newPage();
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

  await browser.close();
  console.log("Screenshots saved to", OUT);
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
