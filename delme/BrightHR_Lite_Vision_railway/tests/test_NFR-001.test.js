const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const { createDb, initDb } = require('../src/db');

function makeRequest(path, port) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: 'localhost',
      port: port,
      path: path,
      method: 'GET'
    }, (res) => {
      res.resume(); // CRITICAL: Consume stream to prevent hanging
      resolve({ statusCode: res.statusCode, headers: res.headers });
    });
    req.on('error', reject);
    req.end();
  });
}

test('Database initializes without errors', async () => {
  process.env.NODE_ENV = 'test';
  const db = createDb();
  await assert.doesNotReject(() => initDb(db));
  db.close();
});

test('Server starts and responds without crashing', { timeout: 30000 }, async () => {
  process.env.NODE_ENV = 'test';
  const app = require('../src/server.js');
  let server;

  try {
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