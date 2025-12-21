import bcrypt from 'bcrypt';
import { createDb } from '../db.js';

const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export async function login(req, res) {
  let db;
  try {
    if (!req.body || !req.body.email || !req.body.password) {
      return res.redirect('/login?error=invalid');
    }

    let email = req.body.email.trim();
    const password = req.body.password.trim();

    if (!emailRegex.test(email)) {
      return res.redirect('/login?error=invalid');
    }

    db = createDb();

    const user = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM users WHERE email = ?', [email], (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(row);
        }
      });
    });

    if (!user) {
      db.close();
      return res.redirect('/login?error=invalid');
    }

    const match = await bcrypt.compare(password, user.password_hash);

    if (match) {
      req.session.user = {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role
      };
      db.close();
      return res.redirect('/dashboard');
    } else {
      db.close();
      return res.redirect('/login?error=invalid');
    }
  } catch (error) {
    console.error(error);
    if (db) db.close();
    res.status(500).send('Internal Server Error');
  }
}

export function logout(req, res) {
  req.session.destroy((err) => {
    if (err) {
      console.error(err);
      return res.status(500).send('Logout Error');
    }
    res.redirect('/login');
  });
}