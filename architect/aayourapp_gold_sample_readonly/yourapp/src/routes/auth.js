const express = require('express');
const bcryptjs = require('bcryptjs');
const router = express.Router();

router.post('/login', async (req, res) => {
  const db = req.app.locals.db;
  const { email, password } = req.body;
  try {
    const user = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE email = ?', [email], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!user || !(await bcryptjs.compare(password, user.password_hash))) {
      return res.status(401).json({ success: false, error: 'Invalid credentials' });
    }
    req.session.userId = user.id;
    req.session.user = { id: user.id, role: user.role };
    req.session.role = user.role;
    res.json({ success: true, redirect: 'dashboard' });
  } catch (e) {
    res.status(500).json({ success: false, error: 'Server error' });
  }
});

router.post('/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      return res.status(500).json({ success: false, error: 'Logout failed' });
    }
    res.clearCookie('connect.sid');
    res.json({ success: true, redirect: 'login' });
  });
});

router.get('/check-session', (req, res) => {
  res.json({ authenticated: !!(req.session && req.session.userId), user: req.session && req.session.user ? { id: req.session.user.id, role: req.session.user.role } : null });
});

module.exports = router;router.get("/debug", (req, res) => res.json({ message: "auth router working" }));
router.get("/test", (req, res) => res.json({ working: true }));
