import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";

// Photo serving depends on request parameters and should not be cached
export const revalidate = 0;


export async function GET(request) {
    const { searchParams } = new URL(request.url);
    const username = searchParams.get("username");
    let folder = searchParams.get("path");
    // Only default to "pending" if path parameter is null/undefined, not if it's empty string
    if (folder === null || folder === undefined) {
        folder = "pending";
    }
    const base = searchParams.get("base") || process.env.USERDATABASE;
    const file = searchParams.get("file");

    console.log("Image request:", { username, folder, base, file });

    if (!username) {
        return NextResponse.json({ error: "Missing username" }, { status: 400 });
    }

    // Fix Windows path separators in folder
    folder = folder.replace(/\\/g, path.sep).replace(/\//g, path.sep);
    let imagePath = null;
    if (file) {
        // Use the exact file name if provided
        imagePath = path.join(base, folder, file);
        if (!fs.existsSync(imagePath)) {
            // Try with username as subfolder
            imagePath = path.join(base, folder, username, file);
        }
    } else {
        // Try multiple image naming conventions
        const possibleNames = [
            `${username}_1.jpg`,
            `${username}.jpg`,
            "1.jpg",
            "photo.jpg",
            "avatar.jpg"
        ];

        // Special case for approved users - images are in username subfolder in base directory
        if (folder === "" || folder === "approved") {
            for (const name of possibleNames) {
                // For approved users, look in base/username/ subfolder
                let candidate = path.join(base, username, name);
                console.log("Trying approved path:", candidate);
                if (fs.existsSync(candidate)) {
                    imagePath = candidate;
                    console.log("Found image at:", imagePath);
                    break;
                }
                // Also try directly in base directory (fallback)
                candidate = path.join(base, name);
                console.log("Trying approved fallback path:", candidate);
                if (fs.existsSync(candidate)) {
                    imagePath = candidate;
                    console.log("Found image at:", imagePath);
                    break;
                }
            }
        } else {
            // For pending and blocked users, use the existing logic
            for (const name of possibleNames) {
                // 1. base/folder/username/name
                let candidate = path.join(base, folder, username, name);
                if (fs.existsSync(candidate)) {
                    imagePath = candidate;
                    break;
                }
                // 2. base/folder/name
                candidate = path.join(base, folder, name);
                if (fs.existsSync(candidate)) {
                    imagePath = candidate;
                    break;
                }
            }
        }
    }
    if (!imagePath || !fs.existsSync(imagePath)) {
        console.error("Image not found:", imagePath);
        return new NextResponse("Not Found", { status: 404 });
    }
    const imageBuffer = fs.readFileSync(imagePath);
    return new NextResponse(imageBuffer, {
        status: 200,
        headers: { "Content-Type": "image/jpeg" }
    });
}
