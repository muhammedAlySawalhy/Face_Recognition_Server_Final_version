import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { verifyToken } from "../../../../lib/auth.js";

// Helper to verify user permissions
function verifyPermission(user, requiredPermission) {
    if (!user) return false;
    if (user.role === 'main-admin') return true;
    if (user.permissions && user.permissions.includes(requiredPermission)) return true;
    return false;
}

// Helper to get authenticated user from request
function getAuthenticatedUser(request) {
    try {
        const authHeader = request.headers.get('authorization');
        const cookieToken = request.cookies.get('adminToken')?.value;
        const token = authHeader?.replace('Bearer ', '') || cookieToken;

        if (!token) return null;
        return verifyToken(token);
    } catch (error) {
        console.error('Auth error:', error);
        return null;
    }
}


// Helper to read users.json
function readUsers() {
    const usersPath = path.join(process.env.GUI_DATA, "users.json");
    if (!fs.existsSync(usersPath)) return [];
    return JSON.parse(fs.readFileSync(usersPath, "utf8"));
}

// Helper to write users.json
function writeUsers(users) {
    const usersPath = path.join(process.env.GUI_DATA, "users.json");
    fs.writeFileSync(usersPath, JSON.stringify(users, null, 2));
}

export async function GET(request) {
    // Check authentication and permissions
    const user = getAuthenticatedUser(request);
    if (!user) {
        return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
    }

    if (!verifyPermission(user, 'edit_user_permissions')) {
        return NextResponse.json({ success: false, error: "Insufficient permissions" }, { status: 403 });
    }

    // List all users (Only users with edit_user_permissions)
    const users = readUsers();
    return NextResponse.json({ success: true, users });
}

export async function POST(request) {
    // Check authentication and permissions
    const authenticatedUser = getAuthenticatedUser(request);
    if (!authenticatedUser) {
        return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
    }

    if (!verifyPermission(authenticatedUser, 'edit_user_permissions')) {
        return NextResponse.json({ success: false, error: "Insufficient permissions" }, { status: 403 });
    }

    // Create user or update permissions (Only users with edit_user_permissions)
    try {
        const body = await request.json();
        const { action, user } = body;
        let users = readUsers();

        if (action === "create") {
            // Create new user
            if (!user || !user.username || !user.password || !user.role) {
                return NextResponse.json({ success: false, message: "Missing user fields" }, { status: 400 });
            }
            if (!user.governments || !Array.isArray(user.governments) || user.governments.length === 0) {
                return NextResponse.json({ success: false, message: "At least one government must be assigned" }, { status: 400 });
            }
            if (users.find(u => u.username === user.username)) {
                return NextResponse.json({ success: false, message: "User already exists" }, { status: 400 });
            }
            // Hash the password before saving
            const { hashPassword } = await import('../../../../lib/auth.js');
            const hashedPassword = await hashPassword(user.password);
            users.push({
                ...user,
                password: hashedPassword,
                permissions: user.permissions || [],
                tabPermissions: user.tabPermissions || [],
                governments: user.governments
            });
            writeUsers(users);
            // Do not return hashed password in response
            const safeUser = { ...user, password: undefined };
            return NextResponse.json({ success: true, message: "User created", user: safeUser });
        }
        if (action === "update-permissions") {
            // Update user permissions and governments if provided
            const { username, permissions, governments } = user;
            const idx = users.findIndex(u => u.username === username);
            if (idx === -1) {
                return NextResponse.json({ success: false, message: "User not found" }, { status: 404 });
            }
            if (permissions) users[idx].permissions = permissions;
            if (governments && Array.isArray(governments)) users[idx].governments = governments;
            writeUsers(users);
            return NextResponse.json({ success: true, message: "Permissions/governments updated", user: users[idx] });
        }
        if (action === "update-tab-permissions") {
            // Update user tab permissions
            const { username, tabPermissions } = user;
            const idx = users.findIndex(u => u.username === username);
            if (idx === -1) {
                return NextResponse.json({ success: false, message: "User not found" }, { status: 404 });
            }
            users[idx].tabPermissions = tabPermissions || [];
            writeUsers(users);
            return NextResponse.json({ success: true, message: "Tab permissions updated", user: users[idx] });
        }
        if (action === "update-password") {
            // Update user password (main-admin only)
            if (authenticatedUser.role !== 'main-admin') {
                return NextResponse.json({ success: false, message: "Only main admin can change passwords" }, { status: 403 });
            }
            const { username, password } = user;
            if (!username || !password) {
                return NextResponse.json({ success: false, message: "Username and password are required" }, { status: 400 });
            }
            const idx = users.findIndex(u => u.username === username);
            if (idx === -1) {
                return NextResponse.json({ success: false, message: "User not found" }, { status: 404 });
            }
            // Hash the new password
            const { hashPassword } = await import('../../../../lib/auth.js');
            const hashedPassword = await hashPassword(password);
            users[idx].password = hashedPassword;
            writeUsers(users);
            return NextResponse.json({ success: true, message: "Password updated successfully" });
        }
        if (action === "delete-user") {
            // Delete user (main-admin only)
            if (authenticatedUser.role !== 'main-admin') {
                return NextResponse.json({ success: false, message: "Only main admin can delete users" }, { status: 403 });
            }
            const { username } = user;
            if (!username) {
                return NextResponse.json({ success: false, message: "Username is required" }, { status: 400 });
            }
            // Prevent self-deletion
            if (username === authenticatedUser.username) {
                return NextResponse.json({ success: false, message: "Cannot delete your own account" }, { status: 400 });
            }
            const idx = users.findIndex(u => u.username === username);
            if (idx === -1) {
                return NextResponse.json({ success: false, message: "User not found" }, { status: 404 });
            }
            // Remove user from array
            users.splice(idx, 1);
            writeUsers(users);
            return NextResponse.json({ success: true, message: "User deleted successfully" });
        }
        return NextResponse.json({ success: false, message: "Invalid action" }, { status: 400 });
    } catch (e) {
        return NextResponse.json({ success: false, message: e.message }, { status: 500 });
    }
}
