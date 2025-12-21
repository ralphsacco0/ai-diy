export function requireRole(requiredRole) {
  return function (req, res, next) {
    if (!req.session?.user?.role || req.session.user.role !== requiredRole) {
      const isApi = req.path.startsWith('/api/') || req.headers.accept?.includes('application/json');
      if (isApi) {
        return res.status(403).json({ success: false, error: 'Access denied' });
      } else {
        return res.redirect('/dashboard?error=access_denied');
      }
    }
    next();
  };
}