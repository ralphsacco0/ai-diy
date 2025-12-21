import sqlite3 from 'sqlite3';
import bcrypt from 'bcrypt';

const isTest = process.env.NODE_ENV === 'test';
const dbPath = isTest ? ':memory:' : './data.sqlite';

function promiseRunNoResult(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

function promiseRun(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function(err) {
      if (err) reject(err);
      else resolve({ id: this.lastID });
    });
  });
}

function promiseGet(db, sql, params = []) {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
}

export function createDb() {
  return new sqlite3.Database(dbPath);
}

export async function initDb(db) {
  try {
    await promiseRunNoResult(db, `CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT DEFAULT 'employee',
      start_date TEXT
    )`);

    const countResult = await promiseGet(db, 'SELECT COUNT(*) as count FROM users');

    if (countResult.count === 0) {
      // Seed admin user
      const adminPassword = 'Password123!';
      const adminHash = await bcrypt.hash(adminPassword, 10);
      await promiseRun(db, 'INSERT INTO users (name, email, password_hash, role, start_date) VALUES (?, ?, ?, ?, ?)',
        ['Admin User', 'admin@test.com', adminHash, 'hr', '2023-01-01']);

      // Seed 5 sample employees
      for (let i = 1; i <= 5; i++) {
        const empName = `Employee ${i}`;
        const empEmail = `emp${i}@company.com`;
        const empHash = await bcrypt.hash('Password123!', 10);
        await promiseRun(db, 'INSERT INTO users (name, email, password_hash, role, start_date) VALUES (?, ?, ?, ?, ?)',
          [empName, empEmail, empHash, 'employee', '2023-01-01']);
      }
    }

    return true;
  } catch (error) {
    throw error;
  }
}