const express = require('express');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

const router = express.Router();

router.get('/', isAuthenticated, isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  const { search, page = 1 } = req.query;
  let sql = 'SELECT * FROM employees';
  let params = [];
  if (search) {
    sql += ' WHERE LOWER(name) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?)';
    params = [`%${search}%`, `%${search}%`];
  }
  const limit = 10;
  const offset = (parseInt(page) - 1) * limit;
  sql += ` LIMIT ${limit} OFFSET ?`;
  params.push(offset);
  try {
    const employees = await new Promise((resolve, reject) => {
      db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
    let countSql = 'SELECT COUNT(*) as total FROM employees';
    let countParams = [];
    if (search) {
      countSql += ' WHERE LOWER(name) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?)';
      countParams = [`%${search}%`, `%${search}%`];
    }
    const count = await new Promise((resolve, reject) => {
      db.get(countSql, countParams, (err, row) => {
        if (err) reject(err);
        else resolve(row.total);
      });
    });
    const totalPages = Math.ceil(count / limit);
    res.json({ employees, total: count, page: parseInt(page), pages: totalPages });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Database error occurred' });
  }
});

router.post('/', isAuthenticated, isHRorAdmin, async (req, res) => {
  try {
    const { name, email, phone, department, hire_date } = req.body;
    if (!name || !email || !hire_date) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    const db = req.app.locals.db;
    const existing = await new Promise((resolve, reject) => {
      db.get('SELECT id FROM employees WHERE email = ?', [email], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (existing) {
      return res.status(400).json({ error: 'Email already exists' });
    }
    const newEmployee = await new Promise((resolve, reject) => {
      db.run('INSERT INTO employees (name, email, phone, department, hire_date) VALUES (?, ?, ?, ?, ?)',
        [name, email, phone || null, department, hire_date],
        function(err) {
          if (err) reject(err);
          else resolve({ id: this.lastID, name, email, phone: phone || null, department, hire_date });
        }
      );
    });
    res.json(newEmployee);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

router.get('/:id', isAuthenticated, isHRorAdmin, async (req, res) => {
  try {
    const id = req.params.id;
    const db = req.app.locals.db;
    const employee = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM employees WHERE id = ?', [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!employee) {
      return res.status(404).json({ error: 'Employee not found' });
    }
    res.json(employee);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

router.patch('/:id', isAuthenticated, isHRorAdmin, async (req, res) => {
  try {
    const id = req.params.id;
    const { name, email, phone, department, hire_date } = req.body;
    if (!name && !email && !phone && !department && !hire_date) {
      return res.status(400).json({ error: 'No fields to update' });
    }
    const db = req.app.locals.db;
    const current = await new Promise((resolve, reject) => {
      db.get('SELECT email FROM employees WHERE id = ?', [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!current) {
      return res.status(404).json({ error: 'Employee not found' });
    }
    if (email && email !== current.email) {
      const existing = await new Promise((resolve, reject) => {
        db.get('SELECT id FROM employees WHERE email = ? AND id != ?', [email, id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
      if (existing) {
        return res.status(400).json({ error: 'Email already exists' });
      }
    }
    const updates = [];
    const params = [];
    if (name !== undefined) {
      updates.push('name = ?');
      params.push(name);
    }
    if (email !== undefined) {
      updates.push('email = ?');
      params.push(email);
    }
    if (phone !== undefined) {
      updates.push('phone = ?');
      params.push(phone);
    }
    if (department !== undefined) {
      updates.push('department = ?');
      params.push(department);
    }
    if (hire_date !== undefined) {
      updates.push('hire_date = ?');
      params.push(hire_date);
    }
    params.push(id);
    const sql = `UPDATE employees SET ${updates.join(', ')} WHERE id = ?`;
    await new Promise((resolve, reject) => {
      db.run(sql, params, function(err) {
        if (err) reject(err);
        else resolve({ changes: this.changes });
      });
    });
    res.json({ success: true, changes: updates.length });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;