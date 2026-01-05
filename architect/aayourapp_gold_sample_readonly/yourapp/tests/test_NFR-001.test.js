const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const { createDb, initDb } = require('../src/db.js');

function makeRequest(path, port) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost',
      port: port,
      path: path,
      method: 'GET'
    }, (res) => {
      res.resume();
      resolve({ statusCode: res.statusCode, headers: res.headers });
    });
    req.on('error', reject);
    req.end();
  });
}

test('Database initializes without errors', async () => {
  let db;
  try {
    process.env.NODE_ENV = 'test';
    db = createDb();
    await assert.doesNotReject(async () => {
      await initDb(db);
    });
  } finally {
    if (db) {
      await new Promise((resolve) => db.close(resolve));
    }
  }
});

test('Server starts and responds without crashing', { timeout: 30000 }, async () => {
  const app = require('../src/server.js');
  let server;
  try {
    process.env.NODE_ENV = 'test';
    server = await new Promise((resolve, reject) => {
      const s = app.listen(0, (err) => {
        if (err) reject(err);
        else resolve(s);
      });
    });
    const port = server.address().port;
    const res = await makeRequest('/', port);
    assert.ok(res.statusCode < 500, `Response status is 5xx: ${res.statusCode}`);
  } finally {
    if (server) {
      await new Promise((resolve) => server.close(resolve));
    }
  }
});