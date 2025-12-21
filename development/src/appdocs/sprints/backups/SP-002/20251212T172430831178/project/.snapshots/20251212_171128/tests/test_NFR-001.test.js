import test from 'node:test';
import assert from 'node:assert';
import http from 'node:http';

async function makeRequest(path, options = {}, port) {
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
      res.resume(); // CRITICAL: Consume response stream
      resolve({
        statusCode: res.statusCode,
        headers: res.headers,
        location: res.headers.location || ''
      });
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

test('Database initializes without errors', async () => {
  const { createDb, initDb } = await import('../src/db.js');
  let db;
  try {
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

test('Server starts and responds without crashing', async () => {
  const { app } = await import('../src/server.js');
  let server;
  try {
    server = await new Promise((resolve, reject) => {
      const s = app.listen(0);
      s.once('listening', () => resolve(s));
      s.once('error', reject);
    });

    const port = server.address().port;
    const res = await makeRequest('/', {}, port);
    assert.ok(res.statusCode < 500, 'Response status is 5xx or higher');
  } finally {
    if (server) {
      server.close();
    }
  }
});