const express = require('express');
const session = require('express-session');
const path = require('path');
const { createDb, initDb } = require('./db');
const authRouter = require('./routes/auth');
const { isAuthenticated } = require('./middleware/auth');

const app = express();

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: process.env.SESSION_SECRET || 'secret-key-change-in-prod',
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 1800000, secure: false, sameSite: 'lax' }
}));
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use("/", authRouter);

app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'login.html'));
});

app.get('/dashboard', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'dashboard.html'));
});

app.get('/', (req, res) => {
  if (req.session && req.session.userId) {
    res.redirect('/dashboard');
  } else {
    res.redirect('/login');
  }
});

app.get('/employees', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'employees.html'));
});

app.get('/leaves', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'leaves.html'));
});

app.get('/documents', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'documents.html'));
});

async function startServer() {
  const db = createDb();
  await initDb(db);
  app.locals.db = db;
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

module.exports = app;

if (require.main === module) {
  startServer();
}