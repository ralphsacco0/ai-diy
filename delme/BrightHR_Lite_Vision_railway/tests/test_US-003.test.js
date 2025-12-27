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

test('Server starts and leaves page route responds without crashing', { timeout: 30000 }, async () => {
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
    // Test leaves page route (protected, expects redirect without crash)
    const leavesRes = await makeRequest('/leaves', {}, port);
    assert.ok(leavesRes.statusCode < 500, `Leaves response status is 5xx: ${leavesRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});

test('Server starts and leaves API endpoint responds without crashing', { timeout: 30000 }, async () => {
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
    // Test leaves API endpoint (protected, expects 403 or similar without crash)
    const apiRes = await makeRequest('/api/leaves/pending', {}, port);
    assert.ok(apiRes.statusCode < 500, `Leaves API response status is 5xx: ${apiRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});