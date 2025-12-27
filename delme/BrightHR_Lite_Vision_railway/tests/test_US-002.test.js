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

test('Server starts and employees page route responds without crashing', { timeout: 30000 }, async () => {
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
    // Test employees page route (protected, expects redirect without crash)
    const employeesRes = await makeRequest('/employees', {}, port);
    assert.ok(employeesRes.statusCode < 500, `Employees response status is 5xx: ${employeesRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});

test('Server starts and employees API endpoint responds without crashing', { timeout: 30000 }, async () => {
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
    // Test employees API endpoint (protected, expects redirect without crash)
    const apiRes = await makeRequest('/api/employees', {}, port);
    assert.ok(apiRes.statusCode < 500, `API response status is 5xx: ${apiRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});