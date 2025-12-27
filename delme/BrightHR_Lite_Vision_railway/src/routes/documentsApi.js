const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

const router = express.Router();

// Multer configuration
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, './uploads');
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + '_' + Math.random() * 1e9 + path.extname(file.originalname));
  }
});

const limits = {
  fileSize: 5242880 // 5MB
};

const fileFilter = function (req, file, cb) {
  if (file.mimetype === 'application/pdf' || file.mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    cb(null, true);
  } else {
    cb(new Error('Invalid file type'), false);
  }
};

const upload = multer({ storage, limits, fileFilter });

router.post('/upload', isAuthenticated, upload.single('file'), async (req, res) => {
  const db = req.app.locals.db;
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }
    const isShared = req.body.share === 'on';
    const employeeId = isShared ? null : req.session.user.id;
    const upload_date = new Date().toISOString().split('T')[0];
    const type = req.body.type;
    await new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO documents (employee_id, filename, original_name, upload_date, type, upload_by_user_id, is_shared) VALUES (?, ?, ?, ?, ?, ?, ?)',
        [employeeId, req.file.filename, req.file.originalname, upload_date, type, req.session.user.id, isShared ? 1 : 0],
        function (err) {
          if (err) reject(err);
          else resolve(this.lastID);
        }
      );
    });
    res.json({ success: true });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.get('/my', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    let sql, params;
    if (req.session.user.role === 'employee') {
      sql = 'SELECT * FROM documents WHERE employee_id = ? OR is_shared = 1 ORDER BY upload_date DESC';
      params = [req.session.user.id];
    } else {
      sql = 'SELECT * FROM documents ORDER BY upload_date DESC';
      params = [];
    }
    const docs = await new Promise((resolve, reject) => {
      db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
    res.json(docs);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.get('/:id/download', isAuthenticated, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const doc = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM documents WHERE id = ?', [req.params.id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!doc) {
      return res.status(404).json({ error: 'Document not found' });
    }
    if (req.session.user.role === 'employee' && doc.employee_id !== req.session.user.id && !doc.is_shared) {
      return res.status(403).json({ error: 'Unauthorized' });
    }
    const filePath = path.join(__dirname, '..', '..', 'uploads', doc.filename);
    if (!fs.existsSync(filePath)) {
      return res.status(404).json({ error: 'File not found' });
    }
    res.download(filePath, doc.original_name);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.delete('/:id', isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const doc = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM documents WHERE id = ?', [req.params.id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    if (!doc) {
      return res.status(404).json({ error: 'Document not found' });
    }
    const filePath = path.join(__dirname, '..', '..', 'uploads', doc.filename);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
    await new Promise((resolve, reject) => {
      db.run('DELETE FROM documents WHERE id = ?', [req.params.id], function (err) {
        if (err) reject(err);
        else resolve();
      });
    });
    res.json({ success: true });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

router.get('/export', isHRorAdmin, async (req, res) => {
  const db = req.app.locals.db;
  try {
    const docs = await new Promise((resolve, reject) => {
      db.all('SELECT * FROM documents', [], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
    const archiver = require('archiver');
    const archive = archiver('zip', { zlib: { level: 9 } });
    res.setHeader('Content-Type', 'application/zip');
    res.attachment('documents.zip');
    archive.pipe(res);
    docs.forEach(doc => {
      const filePath = path.join(__dirname, '..', '..', 'uploads', doc.filename);
      if (fs.existsSync(filePath)) {
        archive.file(filePath, { name: doc.original_name });
      }
    });
    archive.finalize();
    archive.on('error', (err) => {
      console.error(err);
      res.status(500).send(err.message);
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;