import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/tokens.css";
import "./styles/site.css";
import "./styles/hero.css";
import "./styles/sections.css";
import "./styles/teams.css";
import "./styles/docs.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
