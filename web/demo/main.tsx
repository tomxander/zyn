// The online demo: the real review screen, with a stand-in for the API (see mock.ts).
import { installMock } from "./mock";
import "./demo.css";

installMock();

// A slim bar so nobody mistakes the demo for their own data.
const bar = document.createElement("div");
bar.className = "demo-bar";
bar.setAttribute("role", "note");
bar.innerHTML =
  '<span><b>Online demo.</b> Synthetic data (ICX-100), three recorded runs. Decide findings freely: your clicks stay in ' +
  "this tab and vanish on reload. Exports are the real files Zyn made from these runs, before your clicks. Running " +
  "the AI reviewer or checking your own files needs Zyn on your machine.</span>" +
  `<a href="${import.meta.env.BASE_URL.replace(/demo\/$/, "")}">Back to the Zyn site</a>` +
  '<button type="button" aria-label="Hide this note">Hide</button>';
bar.querySelector("button")?.addEventListener("click", () => bar.remove());
document.body.append(bar);

// Pick the first demo run if the address names none.
const u = new URL(location.href);
if (!u.searchParams.get("run")) {
  u.searchParams.set("run", "20261113-235738-c3d95c");
  history.replaceState(null, "", u);
}

import("../src/main");
