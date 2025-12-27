const express = require('express');
const path = require('path');
const { isAuthenticated } = require('../middleware/auth');
const { isHRorAdmin } = require('../middleware/roleCheck');

const router = express.Router();

router.get('/:employee_id', isAuthenticated, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'onboarding.html'));
});

router.get('/pending', isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'onboarding-pending.html'));
});

router.get('/assign', isHRorAdmin, (req, res) => {
  res.sendFile(path.join(__dirname, '..', '..', 'public', 'onboarding-assign.html'));
});

module.exports = router;