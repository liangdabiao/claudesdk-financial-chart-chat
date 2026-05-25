import fs from "fs";
import path from "path";

const LOG_FILE = path.resolve(process.cwd(), "server.log");

export function fileLog(tag: string, ...args: unknown[]) {
  const ts = new Date().toISOString().slice(11, 19);
  const msg = args.map((a) => (typeof a === "string" ? a : JSON.stringify(a))).join(" ");
  const line = `[${ts}] [${tag}] ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line, "utf-8");
}
