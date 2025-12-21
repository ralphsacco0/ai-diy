import express from 'express';
import { login, logout } from '../controllers/authController.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const authRouter = express.Router();

authRouter.post('/login', login);
authRouter.get('/logout', logout);

authRouter.get('/', (req, res, next) => {
  if (req.session?.user) {
    res.redirect('/dashboard');
  } else {
    const filePath = path.join(__dirname, '../../public/login.html');
    res.sendFile(filePath, (err) => {
      if (err) {
        console.error('Error sending login file:', err);
        if (err.code === 'ENOENT') {
          res.status(404).send('Login page not found');
        } else {
          next(err);
        }
      }
    });
  }
});

export { authRouter };