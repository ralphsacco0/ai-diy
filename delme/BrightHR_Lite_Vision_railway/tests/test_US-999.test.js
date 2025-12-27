const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const { createDb, initDb } = require('../src/db');

function makeRequest(path, options = {}, port) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost',
      port: port,
      path: path,
      method: options.method || 'GET',
      headers: {
        'Content-Type': options.contentType || 'application/x-www-form-urlencoded',
        ...options.headers
      }
    }, (res) => {
      res.resume(); // CRITICAL: Consume stream to prevent hanging
      resolve({ statusCode: res.statusCode, headers: res.headers });
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

test('Server starts and dashboard route responds without crashing', { timeout: 30000 }, async () => {
  process.env.NODE_ENV = 'test';
  const app = require('../src/server.js');
  let server;
  let db;

  try {
    db = createDb();
    await initDb(db);
    app.locals.db = db; // Set DB for app use during requests

    server = await new Promise((resolve, reject) => {
      const s = app.listen(0, (err) => {
        if (err) reject(err);
        else resolve(s);
      });
    });

    const port = server.address().port;
    // Test root redirect
    const rootRes = await makeRequest('/', {}, port);
    assert.ok(rootRes.statusCode < 500, `Root response status is 5xx: ${rootRes.statusCode}`);

    // Test login page serve
    const loginRes = await makeRequest('/login', {}, port);
    assert.ok(loginRes.statusCode < 500, `Login response status is 5xx: ${loginRes.statusCode}`);

    // Test dashboard route (protected, expects redirect or auth check without crash)
    const dashboardRes = await makeRequest('/dashboard', {}, port);
    assert.ok(dashboardRes.statusCode < 500, `Dashboard response status is 5xx: ${dashboardRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});