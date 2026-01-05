const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const bcryptjs = require('bcryptjs');

function createDb() {
  const isTest = process.env.NODE_ENV === 'test';
  const dbPath = isTest ? ':memory:' : path.join(__dirname, '..', 'data.sqlite');
  return new sqlite3.Database(dbPath);
}

async function initDb(db) {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
      )`, (err) => {
        if (err) {
          return reject(err);
        }
        db.get('SELECT COUNT(*) as count FROM users', (err, row) => {
          if (err) {
            return reject(err);
          }
          if (row.count === 0) {
            const hashedPassword = bcryptjs.hashSync('Password123!', 12);
            db.run('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
              ['admin@test.com', hashedPassword, 'admin'],
              (err) => {
                if (err) {
                  return reject(err);
                }
                resolve();
              }
            );
          } else {
            resolve();
          }
        });
      });
    });
    db.on('error', (err) => reject(err));
  });
}

module.exports = { createDb, initDb };