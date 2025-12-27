const express = require('express');
const router = express.Router();
const path = require('path');
const bcrypt = require('bcryptjs');
const { isAuthenticated } = require('../middleware/auth');

router.get('/login', (req, res) => {
  if (req.session && req.session.user) {
    return res.redirect('/dashboard');
  }
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'login.html'));
});

router.post('/api/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    const db = req.app.locals.db;
    const user = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE email = ?', [email], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });

    if (user && bcrypt.compareSync(password, user.password_hash)) {
      const fullUser = await new Promise((resolve, reject) => {
        db.get('SELECT u.id, u.email, u.role, e.name FROM users u LEFT JOIN employees e ON u.email = e.email WHERE u.id = ?', [user.id], (err, row) => {
          if (err) reject(err);
          else resolve(row);
        });
      });
      req.session.user = fullUser;
      return res.redirect('/dashboard');
    }

    res.redirect('/login?error=invalid');
  } catch (e) {
    console.error(e);
    res.redirect('/login?error=invalid');
  }
});

router.get('/user', isAuthenticated, async (req, res) => {
  res.json(req.session.user);
});

router.post('/api/auth/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      console.error(err);
    }
    res.redirect('/login');
  });
});

module.exports = router;