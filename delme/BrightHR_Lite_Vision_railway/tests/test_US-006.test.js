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

test('Server starts and employees/add page route responds without crashing', { timeout: 30000 }, async () => {
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
    // Test employees/add page route (protected, expects redirect without crash)
    const addRes = await makeRequest('/employees/add', {}, port);
    assert.ok(addRes.statusCode < 500, `Add employee response status is 5xx: ${addRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});

test('Server starts and employees/edit/:id page route responds without crashing', { timeout: 30000 }, async () => {
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
    // Test employees/edit/1 page route (protected, expects redirect without crash)
    const editRes = await makeRequest('/employees/edit/1', {}, port);
    assert.ok(editRes.statusCode < 500, `Edit employee response status is 5xx: ${editRes.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});