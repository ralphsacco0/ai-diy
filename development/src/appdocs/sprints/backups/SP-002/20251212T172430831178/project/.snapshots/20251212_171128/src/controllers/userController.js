export async function getUser(req, res) {
  try {
    if (!req.session?.user) {
      return res.status(401).json({ success: false, error: 'Unauthorized' });
    }

    const { id, name, email, role } = req.session.user;

    return res.status(200).json({
      success: true,
      data: { id, name, email, role }
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ success: false, error: 'Internal server error' });
  }
}