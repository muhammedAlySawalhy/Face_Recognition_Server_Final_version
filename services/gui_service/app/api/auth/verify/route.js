import { NextResponse } from "next/server";
import jwt from "jsonwebtoken";
// import bcrypt from "bcryptjs"; // Uncomment if password checks are needed here

export async function GET(request) {
    try {
        const authHeader = request.headers.get('authorization');
        const cookieToken = request.cookies.get('adminToken')?.value;
        const token = authHeader?.replace('Bearer ', '') || cookieToken;
        console.log('[DEBUG] /api/auth/verify called');
        console.log('[DEBUG] Received token:', token);
        if (!token) {
            console.log('[DEBUG] No token provided');
            return NextResponse.json({ success: false, isAuthenticated: false, error: "No token provided" }, { status: 401 });
        }
        // Use JWT to verify and decode the token
        let user = null;
        try {
            user = jwt.verify(token, process.env.JWT_SECRET || 'secret');
            console.log(user,"user")
        } catch (jwtError) {
            console.log('[DEBUG] Invalid token:', jwtError);
            return NextResponse.json({ success: false, isAuthenticated: false, error: "Invalid token" }, { status: 401 });
        }
        console.log('[DEBUG] Decoded user from token:', user);
        if (!user) {
            return NextResponse.json({ success: false, isAuthenticated: false, error: "Invalid token" }, { status: 401 });
        }
        // Optionally, you can add more checks here (e.g., user existence in DB)
        return NextResponse.json({ success: true, isAuthenticated: true, user });
    } catch (error) {
        console.error('[DEBUG] Auth verify error:', error);
        return NextResponse.json({ success: false, isAuthenticated: false, error: error.message }, { status: 500 });
    }
}

export async function POST() {
  return NextResponse.json({
    success: false,
    error: 'Method not allowed'
  }, { status: 405 });
}
