const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { createDb, initDb } = require('../src/db.js');

function makeRequest(path, port, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost',
      port: port,
      path: path,
      method: options.method || 'GET',
      headers: {
        'Content-Type': options.contentType || 'application/json',
        ...options.headers
      }
    }, (res) => {
      res.resume();
      resolve({ statusCode: res.statusCode, headers: res.headers });
    });
    req.on('error', reject);
    if (options.body) {
      req.write(options.body);
    }
    req.end();
  });
}

test('Server starts and login page responds without crashing', { timeout: 30000 }, async () => {
  const app = require('../src/server.js');
  let server;
  let db;
  try {
    process.env.NODE_ENV = 'test';
    db = createDb();
    await initDb(db);
    app.locals.db = db;
    server = await new Promise((resolve, reject) => {
      const s = app.listen(0, (err) => {
        if (err) reject(err);
        else resolve(s);
      });
    });
    const port = server.address().port;
    const res = await makeRequest('/login', port);
    assert.ok(res.statusCode < 500, `Response status is 5xx: ${res.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});

test('Auth login endpoint responds without crashing', { timeout: 30000 }, async () => {
  const app = require('../src/server.js');
  let server;
  let db;
  try {
    process.env.NODE_ENV = 'test';
    db = createDb();
    await initDb(db);
    app.locals.db = db;
    server = await new Promise((resolve, reject) => {
      const s = app.listen(0, (err) => {
        if (err) reject(err);
        else resolve(s);
      });
    });
    const port = server.address().port;
    const body = JSON.stringify({ email: 'test@test.com', password: 'wrong' });
    const res = await makeRequest('/api/auth/login', port, {
      method: 'POST',
      contentType: 'application/json',
      body: body
    });
    assert.ok(res.statusCode < 500, `Response status is 5xx: ${res.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});