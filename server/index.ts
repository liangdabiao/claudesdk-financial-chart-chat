import express from "express";
import http from "http";
import { WebSocketServer, WebSocket } from "ws";
import { AgentSession, SDKMessage } from "./agent-client.js";
import { fileLog } from "./logger.js";
import multer from "multer";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config({ override: true });

const PORT = parseInt(process.env.PORT || "3015");
const CHARTS_DIR = path.resolve(process.cwd(), "charts");

process.on("uncaughtException", (e: any) => {
  console.error("uncaughtException:", e?.message || e);
  fileLog("uncaughtException", e?.message || e, e?.stack || "");
});
process.on("unhandledRejection", (e: any) => {
  console.error("unhandledRejection:", e?.message || e);
  fileLog("unhandledRejection", e?.message || e, e?.stack || "");
});

// Ensure charts directory exists
if (!fs.existsSync(CHARTS_DIR)) fs.mkdirSync(CHARTS_DIR, { recursive: true });

const app = express();
app.use(express.json());

// Multer for file upload
const upload = multer({ dest: path.resolve(process.cwd(), "uploads/") });

// Static files - serve built frontend or dev
const distPath = fs.existsSync(path.join(__dirname, "../dist/index.html"))
  ? path.join(__dirname, "../dist")
  : path.join(__dirname, "../../dist");

if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
}

// Serve charts as static images
app.use("/charts", express.static(CHARTS_DIR));

// Chart files tree API
app.get("/api/charts", (_req, res) => {
  try {
    const tree = scanDir(CHARTS_DIR, CHARTS_DIR);
    res.json(tree);
  } catch (e) {
    res.json([]);
  }
});

function scanDir(dir: string, base: string): ChartFile[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).map((entry) => {
    const fullPath = path.join(dir, entry.name);
    const relPath = path.relative(base, fullPath).replace(/\\/g, "/");
    if (entry.isDirectory()) {
      return { name: entry.name, path: relPath, type: "directory", children: scanDir(fullPath, base) };
    }
    return { name: entry.name, path: relPath, type: "file" };
  });
}

interface ChartFile {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: ChartFile[];
}

// Upload API
app.post("/api/upload", upload.array("files", 10), (req, res) => {
  const files = (req.files as Express.Multer.File[]) || [];
  res.json(files.map((f) => ({ name: f.originalname, path: f.path })));
});

// SPA fallback
app.get("*", (_req, res) => {
  const indexPath = path.join(distPath, "index.html");
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.status(404).send("Not found");
  }
});

// HTTP + WebSocket server
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

interface WSClient extends WebSocket {
  sessionId?: string;
}

wss.on("connection", (ws: WSClient) => {
  const sessionId = Math.random().toString(36).slice(2, 8);
  ws.sessionId = sessionId;
  fileLog("WS", "Connected:", sessionId);

  const agent = new AgentSession();

  // Forward agent output to WebSocket
  (async () => {
    try {
      for await (const msg of agent.getOutputStream()) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(msg));
        }
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "done" }));
      }
    } catch (e) {
      fileLog("WS", "Agent stream error:", e);
    }
  })();

  ws.on("message", (raw) => {
    try {
      const data = JSON.parse(raw.toString());
      if (data.type === "message" && data.content) {
        agent.sendMessage(data.content);
      }
    } catch (e) {
      fileLog("WS", "Parse error:", e);
    }
  });

  ws.on("close", () => {
    fileLog("WS", "Disconnected:", sessionId);
    agent.close();
  });
});

server.listen(PORT, () => {
  fileLog("Server", `Listening on http://localhost:${PORT}`);
  console.log(`📊 FinancialChartChat server running on http://localhost:${PORT}`);
});
