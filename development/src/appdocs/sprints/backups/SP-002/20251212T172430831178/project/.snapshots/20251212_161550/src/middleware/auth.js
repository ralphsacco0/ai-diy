export function requireAuth(req, res, next) {
  if (!req.session || !req.session.user) {
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
      return res.redirect('/login');
    } else {
      return res.status(401).json({ success: false, error: 'Unauthorized' });
    }
  }
  next();
}