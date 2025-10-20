import { NextResponse } from "next/server";
import { verifyToken, createUserSession } from "../../../../lib/auth.js";
import fs from "fs";
import path from "path";

// Helper to read users from users.json
function getAllUsers() {
    const usersPath = path.join(process.env.GUI_DATA, 'users.json');
    if (!fs.existsSync(usersPath)) return [];
    return JSON.parse(fs.readFileSync(usersPath, 'utf8'));
}

export async function POST(request) {
    try {
        const authHeader = request.headers.get('authorization');
        const cookieToken = request.cookies.get('adminToken')?.value;
        const token = authHeader?.replace('Bearer ', '') || cookieToken;

        if (!token) {
            return NextResponse.json({
                success: false,
                error: "No token provided"
            }, { status: 401 });
        }

        // Verify current token
        const decoded = verifyToken(token);
        if (!decoded) {
            return NextResponse.json({
                success: false,
                error: "Invalid token"
            }, { status: 401 });
        }

        // Get current user data from database
        const users = getAllUsers();
        const currentUser = users.find(u => u.username === decoded.username);

        if (!currentUser) {
            return NextResponse.json({
                success: false,
                error: "User not found"
            }, { status: 404 });
        }

        // Generate new token with current user data
        const newToken = createUserSession(currentUser);

        const response = NextResponse.json({
            success: true,
            message: 'Token refreshed successfully',
            token: newToken,
            user: {
                username: currentUser.username,
                role: currentUser.role,
                permissions: currentUser.permissions || [],
                tabPermissions: currentUser.tabPermissions || [],
                governments: currentUser.governments || []
            }
        });

        // Set new cookie
        response.cookies.set('adminToken', newToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 60 * 60 * 1000 // 1 hour
        });

        return response;
    } catch (error) {
        console.error('Token refresh error:', error);
        return NextResponse.json({
            success: false,
            error: 'Internal server error'
        }, { status: 500 });
    }
}

export async function GET() {
    return NextResponse.json({
        success: false,
        error: 'Method not allowed'
    }, { status: 405 });
}
