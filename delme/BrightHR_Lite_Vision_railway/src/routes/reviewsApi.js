const express = require('express');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

const router = express.Router();

// POST /create - Create a new performance review (HR only)
router.post('/create', isAuthenticated, isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const { employee_id, review_date, template_type, goals, feedback, next_review_date } = req.body;

    if (!employee_id || !review_date || !template_type || !goals || !feedback || !next_review_date) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    if (!['Annual', 'Quarterly'].includes(template_type)) {
      return res.status(400).json({ error: 'Invalid template_type' });
    }

    const goalsJson = JSON.stringify(goals);
    const reviewer_id = req.session.user.id;

    const result = await new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO performance_reviews (employee_id, review_date, status, template_type, goals, feedback, reviewer_id, next_review_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        [employee_id, review_date, 'draft', template_type, goalsJson, feedback, reviewer_id, next_review_date],
        function (err) {
          if (err) reject(err);
          else resolve({ review_id: this.lastID });
        }
      );
    });

    res.json({ success: true, ...result });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /:employee_id - Get reviews for an employee (authenticated)
router.get('/:employee_id', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const employee_id = req.params.employee_id;

    if (isNaN(employee_id)) {
      return res.status(400).json({ error: 'Invalid employee ID' });
    }

    const reviews = await new Promise((resolve, reject) => {
      db.all(
        'SELECT * FROM performance_reviews WHERE employee_id = ? ORDER BY review_date DESC',
        [employee_id],
        (err, rows) => {
          if (err) reject(err);
          else {
            // Parse goals JSON for each review
            rows.forEach(row => {
              if (row.goals) row.goals = JSON.parse(row.goals);
            });
            resolve(rows);
          }
        }
      );
    });

    res.json(reviews);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// PATCH /:id - Update a performance review (HR only)
router.patch('/:id', isAuthenticated, isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const id = req.params.id;
    const { status, feedback, next_review_date } = req.body;

    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid review ID' });
    }

    if (!status && !feedback && !next_review_date) {
      return res.status(400).json({ error: 'No fields to update' });
    }

    const reviewer_id = req.session.user.id;
    const role = req.session.user.role;

    let updates = [];
    let params = [];

    if (status !== undefined) {
      updates.push('status = ?');
      params.push(status);
    }
    if (feedback !== undefined) {
      updates.push('feedback = ?');
      params.push(feedback);
    }
    if (next_review_date !== undefined) {
      updates.push('next_review_date = ?');
      params.push(next_review_date);
    }

    params.push(id);
    if (role !== 'admin') {
      params.push(reviewer_id);
      updates.push('AND reviewer_id = ?');
    }

    const sql = `UPDATE performance_reviews SET ${updates.join(', ')} WHERE id = ? ${role !== 'admin' ? 'AND reviewer_id = ?' : ''}`;

    const result = await new Promise((resolve, reject) => {
      db.run(sql, params, function (err) {
        if (err) reject(err);
        else if (this.changes === 0) {
          resolve(null); // No changes or not found/unauthorized
        } else {
          // Fetch updated review
          db.get(
            'SELECT * FROM performance_reviews WHERE id = ?',
            [id],
            (err, row) => {
              if (err) reject(err);
              else {
                if (row.goals) row.goals = JSON.parse(row.goals);
                resolve(row);
              }
            }
          );
        }
      });
    });

    if (result === null) {
      return res.status(403).json({ error: 'Unauthorized or not found' });
    }

    res.json(result);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// GET /pending - Get pending reviews (HR only)
router.get('/pending', isAuthenticated, isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const currentDate = new Date().toISOString().split('T')[0];
    const thirtyDaysLater = new Date();
    thirtyDaysLater.setDate(thirtyDaysLater.getDate() + 30);
    const thirtyDaysDate = thirtyDaysLater.toISOString().split('T')[0];

    const reviews = await new Promise((resolve, reject) => {
      db.all(
        "SELECT * FROM performance_reviews WHERE next_review_date <= date(?, '+30 days') AND status != 'completed' ORDER BY next_review_date",
        [currentDate],
        (err, rows) => {
          if (err) reject(err);
          else {
            // Parse goals JSON for each review
            rows.forEach(row => {
              if (row.goals) row.goals = JSON.parse(row.goals);
            });
            resolve(rows);
          }
        }
      );
    });

    res.json(reviews);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
