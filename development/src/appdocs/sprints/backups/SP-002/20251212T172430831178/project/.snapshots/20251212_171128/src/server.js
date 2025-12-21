import 'dotenv/config';
import express from 'express';
import session from 'express-session';
import { authRouter } from './routes/auth.js';
import { pagesRouter } from './routes/pages.js';
import { userRouter } from './routes/user.js';

const app = express();

// Middleware
app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(session({
  secret: process.env.SESSION_SECRET || 'fallback-secret-do-not-use-in-prod',
  resave: false,
  saveUninitialized: false,
  cookie: {
    maxAge: 1800000,
    httpOnly: true,
    secure: false,
    sameSite: 'lax'
  }
}));

app.use('/', authRouter);
app.use('/', pagesRouter);
app.use('/api', userRouter);

app.use(express.static('public'));

// Basic error handler middleware
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ success: false, error: 'Internal server error' });
});

export { app };

// Start server if this file is run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  (async () => {
    try {
      const { createDb, initDb } = await import('./db.js');
      const db = createDb();
      await initDb(db);
      const port = process.env.PORT || 3000;
      const server = app.listen(port, () => {
        console.log(`Server on port ${port}`);
      });
      server.on('error', (err) => {
        console.error('Server error:', err);
        process.exit(1);
      });
    } catch (error) {
      console.error('Failed to start server:', error);
      process.exit(1);
    }
  })();
}