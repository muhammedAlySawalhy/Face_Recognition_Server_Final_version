import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
const JWT_SECRET = process.env.JWT_SECRET || 'omar_ehab_super_secret';
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'admin123';

// Generate JWT token
export function generateToken(payload) {
  // Use jsonwebtoken to sign the payload securely
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '1h' });
}

// Verify JWT token using jsonwebtoken
export function verifyToken(token) {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (error) {
    return null;
  }
}

// Hash password using bcrypt
export async function hashPassword(password) {
  return await bcrypt.hash(password, 12);
}

// Compare password using bcrypt
export async function comparePassword(password, hashedPassword) {
  return await bcrypt.compare(password, hashedPassword);
}

import fs from 'fs';
import path from 'path';

// Read users from users.json
function getAllUsers() {
  const usersPath = path.join(process.env.GUI_DATA, 'users.json');
  if (!fs.existsSync(usersPath)) return [];
  return JSON.parse(fs.readFileSync(usersPath, 'utf8'));
}

export async function verifyUserCredentials(username, password) {
  const users = getAllUsers();
  const user = users.find(u => u.username === username);
  if (!user) return null;

  // Check if password is already hashed (bcrypt hashes start with $2b$ or $2a$)
  const isPasswordHashed = user.password.startsWith('$2b$') || user.password.startsWith('$2a$');

  let match = false;

  if (isPasswordHashed) {
    // Password is already hashed, use bcrypt compare
    match = await comparePassword(password, user.password);
  } else {
    // Password is in plain text, compare directly and then hash it
    match = password === user.password;

    if (match) {
      // User credentials are correct, hash the plain text password
      console.log(`Upgrading plain text password to hashed for user: ${username}`);
      const hashedPassword = await hashPassword(password);

      // Update the user's password in the array
      const userIndex = users.findIndex(u => u.username === username);
      if (userIndex !== -1) {
        users[userIndex].password = hashedPassword;

        // Write back to the JSON file
        const usersPath = path.join(process.env.GUI_DATA, 'users.json');
        try {
          fs.writeFileSync(usersPath, JSON.stringify(users, null, 2));
          console.log(`Password successfully hashed for user: ${username}`);
        } catch (error) {
          console.error(`Failed to update password for user ${username}:`, error);
        }
      }
    }
  }

  if (match) {
    console.log(user, "user")
    return user;
  }
  return null;
}

// Create session for user
export function createUserSession(user) {
  const payload = {
    username: user.username,
    role: user.role,
    permissions: user.permissions || [],
    tabPermissions: user.tabPermissions || [],
    governments: user.governments || [],
    timestamp: Date.now(),
  };
  return generateToken(payload);
}

// Verify admin session
export function verifyAdminSession(token) {
  const decoded = verifyToken(token);
  return decoded && (decoded.role === 'admin' || decoded.role === 'main-admin');
}

// Check if user has admin permissions
export function hasAdminPermissions(user) {
  return user && (user.role === 'admin' || user.role === 'main-admin');
}



// Middleware helper for API routes
export function requireAuth(handler) {
  return async (req, res) => {
    try {
      const token = req.headers.authorization?.replace('Bearer ', '') ||
        req.cookies.adminToken;

      if (!token) {
        return res.status(401).json({
          success: false,
          error: 'Authentication required'
        });
      }

      const user = verifyToken(token);
      if (!user || !hasAdminPermissions(user)) {
        return res.status(403).json({
          success: false,
          error: 'Admin access required'
        });
      }

      // Add user to request object
      req.user = user;
      return handler(req, res);
    } catch (error) {
      return res.status(500).json({
        success: false,
        error: 'Authentication error'
      });
    }
  };
}