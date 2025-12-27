const express = require('express');
const path = require('path');
const auth = require('../middleware/auth');
const roleCheck = require('../middleware/roleCheck');

const router = express.Router();

router.use(auth.isAuthenticated);

router.get('/', (req, res) => {
  if (req.session.user.role === 'employee') {
    res.sendFile(path.join(__dirname, '..', '..', 'public', 'leaves.html'));
  } else {
    res.redirect('/leaves/pending');
  }
});

router.get('/request', async (req, res) => {
  try {
    const user = await new Promise((resolve, reject) => {
      const db = req.app.locals.db;
      db.get('SELECT role FROM users WHERE id = ?', [req.session.user.id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (user.role !== 'employee') {
      return res.redirect('/leaves');
    }
    res.sendFile(path.join(__dirname, '..', '..', 'public', 'leaves-request.html'));
  } catch (err) {
    console.error(err);
    res.status(500).send('Server error');
  }
});

router.get('/pending', roleCheck.isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'leaves-pending.html'));
});

router.get('/calendar', auth.isAuthenticated, roleCheck.isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'leaves-calendar.html'));
});

module.exports = router;