const express = require('express');
const path = require('path');
const { isAuthenticated } = require('../middleware/auth');

const router = express.Router();

router.get('/', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'documents.html'));
});

module.exports = router;