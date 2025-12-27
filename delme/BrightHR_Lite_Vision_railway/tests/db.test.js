const test = require('node:test');
const assert = require('node:assert');

const { createDb, initDb } = require('../src/db');

test('database initializes with admin user', async () => {
  const db = createDb();
  await initDb(db);
  const admin = await new Promise((resolve, reject) => {
    db.get('SELECT * FROM users WHERE email = ?', ['admin@test.com'], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
  assert.strictEqual(admin.email, 'admin@test.com');
  assert(admin.password_hash);
  db.close();
});