import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { requireAuth } from '../middleware/auth.js';
import { requireRole } from '../middleware/rbac.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

router.get('/dashboard', requireAuth, (req, res) => {
  const filePath = path.join(__dirname, '../../public/dashboard.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending dashboard file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('Dashboard page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

// HR-only pages
router.get('/employee-directory', requireAuth, requireRole('hr'), (req, res) => {
  const filePath = path.join(__dirname, '../../public/employee-directory.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending employee-directory file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('Employee Directory page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

router.get('/leave-approvals', requireAuth, requireRole('hr'), (req, res) => {
  const filePath = path.join(__dirname, '../../public/leave-approvals.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending leave-approvals file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('Leave Approvals page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

router.get('/documents', requireAuth, requireRole('hr'), (req, res) => {
  const filePath = path.join(__dirname, '../../public/documents.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending documents file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('Documents page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

// Pages accessible to both roles
router.get('/my-leaves', requireAuth, (req, res) => {
  const filePath = path.join(__dirname, '../../public/my-leaves.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending my-leaves file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('My Leaves page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

router.get('/update-profile', requireAuth, (req, res) => {
  const filePath = path.join(__dirname, '../../public/update-profile.html');
  res.sendFile(filePath, (err) => {
    if (err) {
      console.error('Error sending update-profile file:', err);
      if (err.code === 'ENOENT') {
        res.status(404).send('Update Profile page not found');
      } else {
        res.status(500).send('Internal Server Error');
      }
    }
  });
});

export { router as pagesRouter };