const express = require('express');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

const router = express.Router();

router.post('/assign', isAuthenticated, isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const { employee_id, start_date, tasks } = req.body;
    if (!employee_id || !start_date || !tasks || !Array.isArray(tasks)) {
      return res.status(400).json({ error: 'Missing or invalid required fields' });
    }
    // Ensure all tasks have name, type, completed: false
    const validTasks = tasks.map(task => ({
      name: task.name || '',
      type: task.type || '',
      completed: false
    }));
    const tasksJson = JSON.stringify(validTasks);
    const result = await new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO onboarding_checklists (employee_id, start_date, status, tasks) VALUES (?, ?, ?, ?)',
        [employee_id, start_date, 'in_progress', tasksJson],
        function(err) {
          if (err) reject(err);
          else resolve({ id: this.lastID });
        }
      );
    });
    res.status(201).json(result);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.get('/:employee_id', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const employeeId = parseInt(req.params.employee_id);
    if (isNaN(employeeId)) {
      return res.status(400).json({ error: 'Invalid employee ID' });
    }

    // Check if HR/admin or own employee_id
    let userEmployeeId;
    if (req.session.user.role === 'employee') {
      const employeeRow = await new Promise((resolve, reject) => {
        db.get('SELECT id FROM employees WHERE email = ?', [req.session.user.email], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
      if (!employeeRow) {
        return res.status(404).json({ error: 'Employee record not found' });
      }
      userEmployeeId = employeeRow.id;
      if (userEmployeeId !== employeeId) {
        return res.status(403).json({ error: 'Unauthorized' });
      }
    }

    const checklist = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM onboarding_checklists WHERE employee_id = ?', [employeeId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    if (!checklist) {
      return res.status(404).json({ error: 'Checklist not found' });
    }

    // Parse tasks JSON
    checklist.tasks = JSON.parse(checklist.tasks || '[]');
    res.json(checklist);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.patch('/:id/task/:task_id', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const checklistId = parseInt(req.params.id);
    const taskId = parseInt(req.params.task_id);
    if (isNaN(checklistId) || isNaN(taskId)) {
      return res.status(400).json({ error: 'Invalid ID' });
    }

    // Fetch checklist
    const checklist = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM onboarding_checklists WHERE id = ?', [checklistId], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    if (!checklist) {
      return res.status(404).json({ error: 'Checklist not found' });
    }

    // Check authorization
    if (req.session.user.role === 'employee') {
      const employeeRow = await new Promise((resolve, reject) => {
        db.get('SELECT id FROM employees WHERE email = ?', [req.session.user.email], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
      if (!employeeRow || employeeRow.id !== checklist.employee_id) {
        return res.status(403).json({ error: 'Unauthorized' });
      }
    }

    // Parse tasks
    let tasks = JSON.parse(checklist.tasks || '[]');
    if (taskId < 0 || taskId >= tasks.length) {
      return res.status(400).json({ error: 'Invalid task ID' });
    }

    // Update task
    tasks[taskId].completed = true;

    // Check if all completed
    const allCompleted = tasks.every(task => task.completed);
    const newStatus = allCompleted ? 'completed' : 'in_progress';

    // Save back
    const tasksJson = JSON.stringify(tasks);
    await new Promise((resolve, reject) => {
      db.run(
        'UPDATE onboarding_checklists SET tasks = ?, status = ? WHERE id = ?',
        [tasksJson, newStatus, checklistId],
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });

    res.status(200).json({ success: true, status: newStatus });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.get('/pending', isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const checklists = await new Promise((resolve, reject) => {
      db.all(
        `SELECT oc.*, e.name as employee_name 
         FROM onboarding_checklists oc 
         JOIN employees e ON oc.employee_id = e.id 
         WHERE oc.status = 'in_progress'`,
        [],
        (err, rows) => {
          if (err) reject(err);
          else {
            // Parse tasks for each
            rows.forEach(row => {
              row.tasks = JSON.parse(row.tasks || '[]');
            });
            resolve(rows);
          }
        }
      );
    });
    res.json(checklists);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
