const express = require('express');
const path = require('path');
const { isAuthenticated } = require('../middleware/auth');

const router = express.Router();

router.get('/dashboard', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    res.sendFile(path.join(__dirname, '..', '..', 'public', 'dashboard.html'));
  } catch (err) {
    res.status(500).send('Server error');
  }
});

module.exports = router;