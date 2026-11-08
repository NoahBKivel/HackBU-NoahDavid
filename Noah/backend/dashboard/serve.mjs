import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { watch } from 'node:fs';
import path from 'node:path';
import { homedir } from 'node:os';
import { assets, build, output, root } from './build.mjs';

const portIndex = process.argv.indexOf('--port');
const port = portIndex === -1 ? 4173 : Number(process.argv[portIndex + 1]);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Use a port between 1024 and 65535.');
await build();
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.ttf': 'font/ttf', '.txt': 'text/plain; charset=utf-8' };

async function readJson(filename) {
  try { return JSON.parse(await readFile(filename, 'utf8')); } catch { return {}; }
}
// Keep the Mod's bearer token server-side, outside the static build.
const settings = await readJson(path.join(homedir(), '.claude', 'settings.json'));
const modOptions = settings.pluginConfigs?.vision?.options ?? {};
const secrets = await readJson(path.join(root, '..', 'secrets.local.json'));
const apiUrl = (process.env.VISION_API_URL || modOptions.apiUrl || 'https://davidkny22--alignment-monitor-api.us-east.modal.run').replace(/\/+$/, '');
const apiToken = process.env.VISION_API_TOKEN || modOptions.apiToken || secrets.MONITOR_TOKEN;

const server = createServer(async (request, response) => {
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end();
    return;
  }
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (pathname === '/api/dashboard/sessions') {
    if (!apiToken) {
      response.writeHead(503, { 'Content-Type': 'application/json' }).end(JSON.stringify({ detail: 'Configure the Mod backend token or VISION_API_TOKEN, then restart the server.' }));
      return;
    }
    const upstream = new URL(apiUrl + '/v1/dashboard/sessions');
    const cursor = new URL(request.url, 'http://localhost').searchParams.get('cursor');
    if (cursor) upstream.searchParams.set('cursor', cursor);
    try {
      const result = await fetch(upstream, {
        headers: { authorization: 'Bearer ' + apiToken }, signal: AbortSignal.timeout(12000),
      });
      const body = await result.text();
      response.writeHead(result.status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      response.end(request.method === 'HEAD' ? undefined : body);
    } catch {
      response.writeHead(502, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }).end(JSON.stringify({ detail: 'Could not reach the VISION backend.' }));
    }
    return;
  }
  const name = pathname === '/' ? 'index.html' : pathname.slice(1);
  if (!assets.includes(name)) {
    response.writeHead(404, { 'Content-Type': 'text/plain' }).end('Not found');
    return;
  }
  try {
    const body = await readFile(path.join(output, name));
    response.writeHead(200, {
      'Content-Type': types[path.extname(name)] ?? 'application/octet-stream',
      'Content-Length': body.length,
      'Cache-Control': 'no-store',
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch {
    response.writeHead(500, { 'Content-Type': 'text/plain' }).end('Could not read preview asset');
  }
});

let debounce;
watch(root, { persistent: false }, (_event, filename) => {
  if (!assets.includes(filename)) return;
  clearTimeout(debounce);
  debounce = setTimeout(() => build().catch(error => console.error('Build failed:', error.message)), 100);
});
server.on('error', error => { console.error(error.message); process.exitCode = 1; });
server.listen(port, 'localhost', () => {
  console.log('VISION local preview: http://localhost:' + port);
  console.log('Source changes rebuild automatically. Refresh the browser to see them.');
  console.log('Live dashboard reads from ' + apiUrl + '. Browsing does not invoke the classifier.');
  console.log('For an explicitly labeled synthetic preview, open /?preview=1.');
});
process.on('SIGINT', () => server.close(() => process.exit(0)));
