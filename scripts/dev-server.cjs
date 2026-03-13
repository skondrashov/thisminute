/**
 * Local dev server for thisminute.
 * Serves static files from /static and proxies /api/* to production.
 * Run: node scripts/dev-server.js
 * Then open: http://localhost:3000
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");

const PORT = 3000;
const PROXY_HOST = "thisminute.org";
const STATIC_DIR = path.join(__dirname, "..", "static");

const MIME_TYPES = {
    ".html": "text/html",
    ".js": "application/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".xml": "application/xml",
    ".woff2": "font/woff2",
};

function serveStatic(req, res) {
    // Map / to /static/index.html, /static/* to files
    let filePath;
    if (req.url === "/" || req.url === "/index.html") {
        filePath = path.join(STATIC_DIR, "index.html");
    } else if (req.url.startsWith("/static/")) {
        // Strip query params
        const cleanUrl = req.url.split("?")[0];
        filePath = path.join(STATIC_DIR, cleanUrl.replace("/static/", ""));
    } else {
        return false;
    }

    try {
        if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
            return false;
        }
    } catch {
        return false;
    }

    const ext = path.extname(filePath);
    const contentType = MIME_TYPES[ext] || "application/octet-stream";
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
    return true;
}

function proxyToProduction(req, res) {
    const options = {
        hostname: PROXY_HOST,
        port: 443,
        path: req.url,
        method: req.method,
        headers: {
            ...req.headers,
            host: PROXY_HOST,
        },
    };
    // Remove host/origin that would confuse the proxy
    delete options.headers["host"];
    options.headers["host"] = PROXY_HOST;

    const proxyReq = https.request(options, (proxyRes) => {
        // Don't forward content-encoding since we're passing raw bytes
        const headers = { ...proxyRes.headers };
        res.writeHead(proxyRes.statusCode, headers);
        proxyRes.pipe(res);
    });

    proxyReq.on("error", (err) => {
        console.error(`Proxy error: ${err.message}`);
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Proxy error", detail: err.message }));
    });

    req.pipe(proxyReq);
}

const server = http.createServer((req, res) => {
    // Try static files first (local CSS/JS/HTML)
    if (req.url === "/" || req.url === "/index.html" || req.url.startsWith("/static/")) {
        if (serveStatic(req, res)) return;
    }

    // Everything else (API calls, favicon, etc.) → proxy to production
    proxyToProduction(req, res);
});

server.listen(PORT, () => {
    console.log(`\n  thisminute dev server running at http://localhost:${PORT}`);
    console.log(`  Static files: ${STATIC_DIR}`);
    console.log(`  API proxy: https://${PROXY_HOST}`);
    console.log(`\n  Edit CSS/JS locally, refresh to see changes.\n`);
});
