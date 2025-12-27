const sqlite3 = require('sqlite3');
const bcrypt = require('bcryptjs');
const path = require('path');
const fs = require('fs');

// Factory function to create database connection
function createDb() {
  const dbPath = process.env.NODE_ENV === 'test' ? ':memory:' : path.join(__dirname, '..', 'data.sqlite');
  return new sqlite3.Database(dbPath);
}

function seedEmployeeUsers(db, callback) {
  const employeeEmails = [
    'john@company.com',
    'jane@company.com',
    'bob@company.com',
    'alice@company.com',
    'charlie@company.com'
  ];
  let index = 0;

  function checkAndInsert() {
    if (index >= employeeEmails.length) {
      callback(null);
      return;
    }
    const email = employeeEmails[index];
    db.get('SELECT COUNT(*) as cnt FROM users WHERE email = ?', [email], (err, row) => {
      if (err) {
        callback(err);
        return;
      }
      if (row.cnt === 0) {
        const hash = bcrypt.hashSync('Password123!', 12);
        db.run('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)', [email, hash, 'employee'], (err) => {
          if (err) {
            callback(err);
            return;
          }
          index++;
          checkAndInsert();
        });
      } else {
        index++;
        checkAndInsert();
      }
    });
  }
  checkAndInsert();
}

function createEmployees(db, callback) {
  db.run(`CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    department TEXT,
    hire_date TEXT
  )`, (err) => {
    if (err) {
      return callback(err);
    }

    db.get('SELECT COUNT(*) as cnt FROM employees', (err, row) => {
      if (err) {
        return callback(err);
      }

      if (row.cnt === 0) {
        const employees = [
          ['John Doe', 'john@company.com', '555-0123', 'HR', '2023-01-15'],
          ['Jane Smith', 'jane@company.com', '555-0124', 'Engineering', '2023-02-01'],
          ['Bob Johnson', 'bob@company.com', '555-0125', 'Sales', '2023-03-10'],
          ['Alice Brown', 'alice@company.com', '555-0126', 'Marketing', '2023-04-05'],
          ['Charlie Wilson', 'charlie@company.com', '555-0127', 'IT', '2023-05-20']
        ];
        let insertIndex = 0;

        function insertNext() {
          if (insertIndex >= employees.length) {
            callback(null);
            return;
          }
          const emp = employees[insertIndex];
          db.run(
            'INSERT OR IGNORE INTO employees (name, email, phone, department, hire_date) VALUES (?, ?, ?, ?, ?)',
            emp,
            (err) => {
              if (err) {
                callback(err);
                return;
              }
              insertIndex++;
              insertNext();
            }
          );
        }
        insertNext();
      } else {
        callback(null);
      }
    });
  });
}

function createAdditionalEmployees(db, callback) {
  const promise = new Promise((resolve, reject) => {
    (async () => {
      try {
        const count = await new Promise((res, rej) => {
          db.all('SELECT COUNT(*) as count FROM employees', (err, rows) => {
            if (err) rej(err);
            else res(rows[0].count);
          });
        });
        if (count < 7) {
          const additionalEmployees = [
            ['Jane Smith', 'jane.smith@company.com', '555-0124', 'Sales', '2023-06-01'],
            ['Bob Johnson', 'bob.johnson@company.com', '555-0125', 'IT', '2023-03-15']
          ];
          for (const emp of additionalEmployees) {
            await new Promise((res, rej) => {
              db.run('INSERT INTO employees (name, email, phone, department, hire_date) VALUES (?, ?, ?, ?, ?)', 
                emp, 
                function(err) {
                  if (err) rej(err);
                  else res(this.lastID);
                }
              );
            });
          }
        }
        resolve();
      } catch (err) {
        reject(err);
      }
    })();
  });
  promise.then(() => callback(null)).catch(callback);
}

function createLeaves(db, callback) {
  db.run(`CREATE TABLE IF NOT EXISTS leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    approver_id INTEGER,
    notes TEXT
  )`, (err) => {
    if (err) {
      return callback(err);
    }

    db.get('SELECT COUNT(*) as cnt FROM leaves', (err, row) => {
      if (err) {
        return callback(err);
      }

      if (row.cnt === 0) {
        const getId = (table, email) => {
          return new Promise((resolve, reject) => {
            db.get(`SELECT id FROM ${table} WHERE email = ?`, [email], (err, row) => {
              if (err) {
                reject(err);
              } else {
                resolve(row ? row.id : null);
              }
            });
          });
        };

        const insertLeave = (params, sql, values) => {
          return new Promise((resolve, reject) => {
            db.run(sql, values, (err) => {
              if (err) {
                reject(err);
              } else {
                resolve();
              }
            });
          });
        };

        async function seedLeaves() {
          try {
            const adminId = await getId('users', 'admin@test.com');
            const johnId = await getId('employees', 'john@company.com');
            await insertLeave(
              {},
              'INSERT INTO leaves (employee_id, start_date, end_date, type, status, notes) VALUES (?, ?, ?, ?, ?, ?)',
              [johnId, '2024-10-01', '2024-10-05', 'vacation', 'pending', 'Vacation time']
            );
            const janeId = await getId('employees', 'jane@company.com');
            await insertLeave(
              {},
              'INSERT INTO leaves (employee_id, start_date, end_date, type, status, approver_id, notes) VALUES (?, ?, ?, ?, ?, ?, ?)',
              [janeId, '2024-09-01', '2024-09-03', 'sick', 'approved', adminId, 'Illness']
            );
            callback(null);
          } catch (err) {
            callback(err);
          }
        }
        seedLeaves();
      } else {
        callback(null);
      }
    });
  });
}

function createDocuments(db, callback) {
  db.run(`CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    filename TEXT NOT NULL,
    original_name TEXT NOT NULL,
    upload_date TEXT NOT NULL,
    type TEXT NOT NULL,
    upload_by_user_id INTEGER NOT NULL,
    is_shared INTEGER DEFAULT 0,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
  )`, (err) => {
    if (err) {
      return callback(err);
    }

    db.get('SELECT COUNT(*) as cnt FROM documents', (err, row) => {
      if (err) {
        return callback(err);
      }

      if (row.cnt === 0) {
        const uploadsPath = path.join(__dirname, '..', '..', 'uploads');
        fs.mkdirSync(uploadsPath, { recursive: true });

        const contractPath = path.join(uploadsPath, 'seed_contract.pdf');
        if (!fs.existsSync(contractPath)) {
          fs.writeFileSync(contractPath, '');
        }

        const policyPath = path.join(uploadsPath, 'seed_policy.docx');
        if (!fs.existsSync(policyPath)) {
          fs.writeFileSync(policyPath, '');
        }

        const uploadDate = new Date().toISOString().split('T')[0];

        db.run(`INSERT INTO documents (employee_id, filename, original_name, upload_date, type, upload_by_user_id, is_shared) 
                VALUES (?, ?, ?, ?, ?, ?, ?)`, 
                [1, 'seed_contract.pdf', 'contract.pdf', uploadDate, 'contract', 1, 0], (err) => {
          if (err) {
            return callback(err);
          }
          db.run(`INSERT INTO documents (employee_id, filename, original_name, upload_date, type, upload_by_user_id, is_shared) 
                  VALUES (?, ?, ?, ?, ?, ?, ?)`, 
                  [null, 'seed_policy.docx', 'policy.docx', uploadDate, 'policy', 1, 1], (err) => {
            if (err) {
              return callback(err);
            }
            callback(null);
          });
        });
      } else {
        callback(null);
      }
    });
  });
}

function createOnboardingChecklists(db, callback) {
  db.run(`CREATE TABLE IF NOT EXISTS onboarding_checklists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress' CHECK(status IN ('in_progress', 'completed')),
    tasks TEXT NOT NULL,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
  )`, (err) => {
    if (err) {
      return callback(err);
    }

    db.get('SELECT COUNT(*) as cnt FROM onboarding_checklists', (err, row) => {
      if (err) {
        return callback(err);
      }

      if (row.cnt === 0) {
        const tasksJson = '[{ "name": "Upload ID", "type": "upload", "completed": false }, { "name": "Acknowledge Policies", "type": "checkbox", "completed": false }, { "name": "Complete IT Setup", "type": "checkbox", "completed": false }]';
        db.run(
          'INSERT INTO onboarding_checklists (employee_id, start_date, tasks, status) VALUES (?, ?, ?, ?)',
          [1, '2024-01-01', tasksJson, 'in_progress'],
          (err) => {
            if (err) {
              callback(err);
            } else {
              callback(null);
            }
          }
        );
      } else {
        callback(null);
      }
    });
  });
}

function createPerformanceReviews(db, callback) {
  db.run(`CREATE TABLE IF NOT EXISTS performance_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    review_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    template_type TEXT NOT NULL,
    goals TEXT,
    feedback TEXT,
    reviewer_id INTEGER,
    next_review_date TEXT,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
  )`, (err) => {
    if (err) {
      return callback(err);
    }

    db.get('SELECT COUNT(*) as cnt FROM performance_reviews', (err, row) => {
      if (err) {
        return callback(err);
      }

      if (row.cnt === 0) {
        const goalsJson = JSON.stringify([{name: 'Improve communication', target: 'Attend workshops'}]);
        db.run(
          'INSERT INTO performance_reviews (employee_id, review_date, status, template_type, goals, feedback, reviewer_id, next_review_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
          [1, '2024-01-01', 'completed', 'Annual', goalsJson, 'Strong performer, meets all goals', 1, '2025-01-01'],
          (err) => {
            if (err) {
              callback(err);
            } else {
              callback(null);
            }
          }
        );
      } else {
        callback(null);
      }
    });
  });
}

// Async initializer to create tables and seed data
async function initDb(db) {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        role TEXT NOT NULL CHECK(role IN ('admin', 'hr', 'employee'))
      )`, (err) => {
        if (err) {
          return reject(err);
        }

        db.get('SELECT COUNT(*) as cnt FROM users', (err, row) => {
          if (err) {
            return reject(err);
          }

          function afterAdmin() {
            seedEmployeeUsers(db, (err) => {
              if (err) {
                reject(err);
                return;
              }
              createEmployees(db, (err) => {
                if (err) {
                  reject(err);
                  return;
                }
                createAdditionalEmployees(db, (err) => {
                  if (err) {
                    reject(err);
                    return;
                  }
                  createLeaves(db, (err) => {
                    if (err) {
                      reject(err);
                      return;
                    }
                    createDocuments(db, (err) => {
                      if (err) {
                        reject(err);
                      } else {
                        createOnboardingChecklists(db, (err) => {
                          if (err) {
                            reject(err);
                          } else {
                            createPerformanceReviews(db, (err) => {
                              if (err) {
                                reject(err);
                              } else {
                                resolve();
                              }
                            });
                          }
                        });
                      }
                    });
                  });
                });
              });
            });
          }

          if (row.cnt === 0) {
            bcrypt.hash('Password123!', 12, (err, hash) => {
              if (err) {
                return reject(err);
              }
              db.run(
                'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
                ['admin@test.com', hash, 'admin'],
                (err) => {
                  if (err) {
                    return reject(err);
                  }
                  afterAdmin();
                }
              );
            });
          } else {
            afterAdmin();
          }
        });
      });
    });
  });
}

module.exports = { createDb, initDb };