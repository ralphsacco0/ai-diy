const express = require('express');
const router = express.Router();
const path = require('path');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

router.get('/employees', isAuthenticated, isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'employees.html'));
});

router.get('/employees/add', isAuthenticated, isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'employees-add.html'));
});

router.get('/employees/edit/:id', isAuthenticated, isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'employees-edit.html'));
});

module.exports = router;