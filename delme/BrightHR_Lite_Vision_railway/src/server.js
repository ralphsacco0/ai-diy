const express = require('express');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const authRoutes = require('./routes/auth');
const dashboardRouter = require('./routes/dashboard');
const { createDb, initDb } = require('./db');
const employeesApiRouter = require('./routes/employeesApi');
const leavesApiRouter = require('./routes/leavesApi');
const leavesRouter = require('./routes/leaves');
const documentsRouter = require('./routes/documents');
const documentsApiRouter = require('./routes/documentsApi');
const employeesRoutes = require('./routes/employees');
const onboardingApiRouter = require('./routes/onboardingApi');
const onboardingRouter = require('./routes/onboarding');
const reviewsApiRouter = require('./routes/reviewsApi');
const { isAuthenticated } = require('./middleware/auth');
const { isHRorAdmin } = require('./middleware/roleCheck');

const app = express();

// Middleware configuration in order
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: process.env.SESSION_SECRET || 'dev-secret',
  resave: false,
  saveUninitialized: false,
  cookie: { maxAge: 30 * 60 * 1000, secure: false, sameSite: 'lax' }
}));
app.use(express.static('public'));
app.use('/', authRoutes);
app.use('/', dashboardRouter);
app.use('/api/employees', employeesApiRouter);
app.use('/api/leaves', leavesApiRouter);
app.use('/leaves', leavesRouter);
app.use('/documents', documentsRouter);
app.use('/api/documents', documentsApiRouter);
app.use('/', employeesRoutes);
app.use('/api/onboarding', onboardingApiRouter);
app.use('/', onboardingRouter);
app.use('/api/reviews', reviewsApiRouter);

app.get('/', (req, res) => {
  if (req.session && req.session.user) {
    res.redirect('/dashboard');
  } else {
    res.redirect('/login');
  }
});

// Async start server function
async function startServer() {
  const db = createDb();
  await initDb(db);
  const uploadsPath = path.join(__dirname, '..', 'uploads');
  if (!fs.existsSync(uploadsPath)) {
    fs.mkdirSync(uploadsPath, { recursive: true });
  }
  app.locals.db = db;
  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Server running on port ${port}`);
  });
}

// Export app for tests
module.exports = app;

// Start server if run directly
if (require.main === module) {
  startServer().catch(console.error);
}