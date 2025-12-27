const express = require('express');
const { isAuthenticated } = require('../middleware/auth');
const auth = require('../middleware/auth');
const roleCheck = require('../middleware/roleCheck');

const router = express.Router();

router.use(isAuthenticated);

router.post('/request', async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (req.session.user.role !== 'employee') {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    const user = req.session.user;
    const employeeRow = await new Promise((resolve, reject) => {
      db.get('SELECT id FROM employees WHERE email = ?', [user.email], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!employeeRow) {
      return res.status(400).json({ error: 'No employee record' });
    }
    const { start_date, end_date, type, reason } = req.body;
    if (!start_date || !end_date || !type || new Date(end_date) <= new Date(start_date)) {
      return res.status(400).json({ error: 'Invalid dates or required fields' });
    }
    await new Promise((resolve, reject) => {
      db.run('INSERT INTO leaves (employee_id, start_date, end_date, type, status, notes) VALUES (?, ?, ?, ?, ?, ?)',
        [employeeRow.id, start_date, end_date, type, 'pending', reason || ''],
        function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        }
      );
    });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/my-requests', async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (req.session.user.role !== 'employee') {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    const user = req.session.user;
    const employeeRow = await new Promise((resolve, reject) => {
      db.get('SELECT id FROM employees WHERE email = ?', [user.email], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!employeeRow) {
      return res.status(400).json({ error: 'No employee record' });
    }
    const rows = await new Promise((resolve, reject) => {
      db.all('SELECT * FROM leaves WHERE employee_id = ? ORDER BY start_date DESC', [employeeRow.id], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/pending', async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (!['hr', 'admin'].includes(req.session.user.role)) {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    const rows = await new Promise((resolve, reject) => {
      db.all(`SELECT l.*, e.name as employee_name FROM leaves l 
              JOIN employees e ON l.employee_id = e.id 
              WHERE l.status = ? ORDER BY l.start_date`,
        ['pending'],
        (err, rows) => {
          if (err) reject(err);
          else resolve(rows);
        }
      );
    });
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/approve/:id', async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (!['hr', 'admin'].includes(req.session.user.role)) {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    const { changes } = await new Promise((resolve, reject) => {
      const id = req.params.id;
      db.run('UPDATE leaves SET status = ?, approver_id = ? WHERE id = ? AND status = ?',
        ['approved', req.session.user.id, id, 'pending'],
        function(err) {
          if (err) reject(err);
          else resolve({ changes: this.changes });
        }
      );
    });
    if (changes === 0) {
      return res.status(400).json({ error: 'Not found or already processed' });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/reject/:id', async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (!['hr', 'admin'].includes(req.session.user.role)) {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    if (!req.body.reason || req.body.reason.trim() === '') {
      return res.status(400).json({ error: 'Reason required' });
    }
    const { changes } = await new Promise((resolve, reject) => {
      const id = req.params.id;
      db.run('UPDATE leaves SET status = ?, notes = ?, approver_id = ? WHERE id = ? AND status = ?',
        ['rejected', req.body.reason, req.session.user.id, id, 'pending'],
        function(err) {
          if (err) reject(err);
          else resolve({ changes: this.changes });
        }
      );
    });
    if (changes === 0) {
      return res.status(400).json({ error: 'Not found or already processed' });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/calendar', auth.isAuthenticated, roleCheck.isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  const year = req.query.year || new Date().getFullYear().toString();
  const monthNum = parseInt(req.query.month) || (new Date().getMonth() + 1);
  const month = monthNum.toString().padStart(2, '0');
  const startOfMonth = `${year}-${month}-01`;
  const lastDay = new Date(parseInt(year), monthNum, 0).getDate();
  const endOfMonth = `${year}-${month}-${lastDay.toString().padStart(2, '0')}`;
  let sql = `SELECT e.name as employee_name, l.start_date, l.end_date, l.type, l.status FROM leaves l JOIN employees e ON l.employee_id = e.id WHERE l.start_date <= ? AND l.end_date >= ? AND l.status IN ('approved', 'pending')`;
  let params = [endOfMonth, startOfMonth];
  if (req.query.type && req.query.type !== 'All Types') {
    sql += ` AND l.type = ?`;
    params.push(req.query.type);
  }
  if (req.query.employee_name && req.query.employee_name !== 'All Employees') {
    sql += ` AND e.name LIKE ?`;
    params.push(`%${req.query.employee_name}%`);
  }
  try {
    const events = await new Promise((resolve, reject) => {
      db.all(sql, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          const processed = rows.map(row => ({
            ...row,
            color_code: row.type === 'vacation' ? 'vacation' : row.type === 'sick' ? 'sick' : 'other'
          }));
          resolve(processed);
        }
      });
    });
    res.json(events);
  } catch (error) {
    res.status(500).json({ error: 'Database error' });
  }
});

module.exports = router;
