import express from 'express';
import { requireAuth } from '../middleware/auth.js';
import { getUser } from '../controllers/userController.js';

const router = express.Router();

router.get('/user', requireAuth, getUser);

export { router as userRouter };