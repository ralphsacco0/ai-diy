module.exports = {
  isHRorAdmin: (req, res, next) => {
    if (!req.session?.user || (req.session.user.role !== 'hr' && req.session.user.role !== 'admin')) {
      return res.redirect('/login?error=unauthorized');
    }
    next();
  }
};