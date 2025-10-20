import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import sharp from "sharp";

// User creation involves filesystem operations and should not be cached
export const revalidate = 0;

// Get user database root from env
const USERDATABASE = process.env.USERDATABASE;
const GUI_DATA = process.env.GUI_DATA;

function ensureDirSync(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

// Helpers
function pendingDir(username) {
  return path.join(GUI_DATA, "pending", username);
}
function rejectedDir(username) {
  return path.join(GUI_DATA, "rejected", username);
}
function blockedDir(username) {
  return path.join(GUI_DATA, "blocked", username);
}
function pausedDir(username) {
  return path.join(GUI_DATA, "paused", username);
}
function approvedDir(username) {
  return path.join(USERDATABASE, username);
}
function imageName(username) {
  return `${username}_1.jpg`;
}

async function writeOrCropImage(imageData, destPath) {
  if (!imageData) throw new Error("Image data is required");
  const base64Data = imageData.replace(/^data:image\/\w+;base64,/, "");
  const imgBuffer = Buffer.from(base64Data, "base64");
  const metadata = await sharp(imgBuffer).metadata();
  if (!metadata.width || !metadata.height || metadata.width < 240 || metadata.height < 240) {
    throw new Error("Image must be at least 240x240 pixels");
  }
  const minDim = Math.min(metadata.width, metadata.height);
  const squaredBuffer = await sharp(imgBuffer)
    .extract({
      left: Math.floor((metadata.width - minDim) / 2),
      top: Math.floor((metadata.height - minDim) / 2),
      width: minDim,
      height: minDim,
    })
    .resize(240, 240)
    .jpeg()
    .toBuffer();
  fs.writeFileSync(destPath, squaredBuffer);
}

function copyIfExists(src, dest) {
  if (!fs.existsSync(src)) {
    throw new Error("Source image not found");
  }
  ensureDirSync(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

function writeInfo(dir, info) {
  ensureDirSync(dir);
  fs.writeFileSync(path.join(dir, "info.json"), JSON.stringify(info, null, 2));
}

const ACTIONS = {
  // New user submission without status -> create pending with cropped image
  pending: async ({ username, nationalId, userInfo, imageData }) => {
    // If user already exists, remove the existing directory first
    const dir = pendingDir(username);

    // Clean up any existing directories for this user (override behavior)
    const possibleDirs = [
      pendingDir(username),
      approvedDir(username),
      rejectedDir(username),
      blockedDir(username),
      pausedDir(username)
    ];

    possibleDirs.forEach(dirPath => {
      try {
        if (fs.existsSync(dirPath)) {
          fs.rmSync(dirPath, { recursive: true, force: true });
        }
      } catch (error) {
        console.warn(`Could not remove existing directory ${dirPath}:`, error.message);
      }
    });

    ensureDirSync(dir);
    await writeOrCropImage(imageData, path.join(dir, imageName(username)));

    // Save comprehensive user info from Excel data
    const infoData = {
      username,
      nationalId,
      name: userInfo?.name || '',
      department: userInfo?.department || '',
      government: userInfo?.government || '',
      status: "pending",
      createdAt: new Date().toISOString(),
      image: imageName(username),
      ...userInfo // Include any additional fields from Excel
    };

    writeInfo(dir, infoData);
    return { dir, message: `User ${userInfo?.name || username} (${nationalId}) pending and image saved (overridden if existed)` };
  },
  // Approve from pending -> move to USERDATABASE
  approve: async ({ username, nationalId, userInfo }) => {
    const srcDir = pendingDir(username);
    const destDir = approvedDir(username);
    const srcImage = path.join(srcDir, imageName(username));
    const destImage = path.join(destDir, imageName(username));

    // Read existing info.json from pending if it exists
    let existingInfo = {};
    const infoPath = path.join(srcDir, "info.json");
    try {
      if (fs.existsSync(infoPath)) {
        existingInfo = JSON.parse(fs.readFileSync(infoPath, 'utf8'));
      }
    } catch (error) {
      console.warn("Could not read existing info.json:", error.message);
    }

    copyIfExists(srcImage, destImage);
    // remove pending folder
    try { fs.rmSync(srcDir, { recursive: true, force: true }); } catch { }

    // Preserve existing user info and update status
    const finalInfo = {
      ...existingInfo,
      username,
      status: "approved",
      createdAt: existingInfo.createdAt || new Date().toISOString(),
      approvedAt: new Date().toISOString(),
      image: imageName(username)
    };

    // Add nationalId and userInfo if provided
    if (nationalId) finalInfo.nationalId = nationalId;
    if (userInfo) {
      finalInfo.name = userInfo.name || finalInfo.name || '';
      finalInfo.department = userInfo.department || finalInfo.department || '';
      finalInfo.government = userInfo.government || finalInfo.government || '';
    }

    writeInfo(destDir, finalInfo);
    return { dir: destDir, message: `User ${finalInfo.name || username} approved` };
  },
  // Reject: filesystem-only move to GUI_DATA/rejected
  reject: async ({ username, nationalId, userInfo }) => {
    const approvedSrc = approvedDir(username);
    const pendingSrc = pendingDir(username);
    const srcDir = fs.existsSync(approvedSrc) ? approvedSrc : pendingSrc;
    if (!fs.existsSync(srcDir)) {
      throw new Error("User directory not found in available or pending");
    }

    // Read existing info.json if it exists
    let existingInfo = {};
    const infoPath = path.join(srcDir, "info.json");
    try {
      if (fs.existsSync(infoPath)) {
        existingInfo = JSON.parse(fs.readFileSync(infoPath, 'utf8'));
      }
    } catch (error) {
      console.warn("Could not read existing info.json:", error.message);
    }

    const destDir = rejectedDir(username);
    // Ensure destination parent exists and clean old dest if present
    ensureDirSync(path.dirname(destDir));
    try { fs.rmSync(destDir, { recursive: true, force: true }); } catch { }
    try {
      fs.renameSync(srcDir, destDir);
    } catch (e) {
      if (fs.cpSync) {
        fs.cpSync(srcDir, destDir, { recursive: true });
        try { fs.rmSync(srcDir, { recursive: true, force: true }); } catch { }
      } else {
        const srcImage = path.join(srcDir, imageName(username));
        const destImage = path.join(destDir, imageName(username));
        copyIfExists(srcImage, destImage);

        // Preserve existing user info and update status
        const finalInfo = {
          ...existingInfo,
          username,
          status: "rejected",
          createdAt: existingInfo.createdAt || new Date().toISOString(),
          rejectedAt: new Date().toISOString(),
          image: imageName(username)
        };

        // Add nationalId and userInfo if provided
        if (nationalId) finalInfo.nationalId = nationalId;
        if (userInfo) {
          finalInfo.name = userInfo.name || finalInfo.name || '';
          finalInfo.department = userInfo.department || finalInfo.department || '';
          finalInfo.government = userInfo.government || finalInfo.government || '';
        }

        writeInfo(destDir, finalInfo);
        try { fs.rmSync(srcDir, { recursive: true, force: true }); } catch { }
      }
    }
    return { dir: destDir, message: `User ${existingInfo.name || username} rejected (moved to rejected)` };
  },
  // Block: runtime/Redis-only, no filesystem change via this route
  block: async ({ username }) => {
    return { dir: null, message: `User ${username} blocked (no filesystem changes)` };
  },
  // Pause overlay copy (filesystem), available preserved
  pause: async ({ username, nationalId, userInfo }) => {
    const approvedImage = path.join(approvedDir(username), imageName(username));
    const destDir = pausedDir(username);
    const destImage = path.join(destDir, imageName(username));

    // Read existing info.json from approved directory if it exists
    let existingInfo = {};
    const infoPath = path.join(approvedDir(username), "info.json");
    try {
      if (fs.existsSync(infoPath)) {
        existingInfo = JSON.parse(fs.readFileSync(infoPath, 'utf8'));
      }
    } catch (error) {
      console.warn("Could not read existing info.json:", error.message);
    }

    copyIfExists(approvedImage, destImage);

    // Preserve existing user info and update status
    const finalInfo = {
      ...existingInfo,
      username,
      status: "paused",
      createdAt: existingInfo.createdAt || new Date().toISOString(),
      pausedAt: new Date().toISOString(),
      image: imageName(username)
    };

    // Add nationalId and userInfo if provided
    if (nationalId) finalInfo.nationalId = nationalId;
    if (userInfo) {
      finalInfo.name = userInfo.name || finalInfo.name || '';
      finalInfo.department = userInfo.department || finalInfo.department || '';
      finalInfo.government = userInfo.government || finalInfo.government || '';
    }

    writeInfo(destDir, finalInfo);
    return { dir: destDir, message: `User ${finalInfo.name || username} paused (available preserved)` };
  },
};

export async function POST(request) {
  try {
    const { username, nationalId, userInfo, imageData, action } = await request.json();

    if (!username) {
      return NextResponse.json({ error: "Username is required" }, { status: 400 });
    }

    // Determine action; default to pending when creating new user with image
    let resolvedAction = action;
    if (!resolvedAction) {
      resolvedAction = imageData ? "pending" : "approve"; // fallback
    }

    // National ID is only required for 'pending' action (new user creation)
    if (resolvedAction === "pending" && !nationalId) {
      return NextResponse.json({ error: "National ID is required for new user creation" }, { status: 400 });
    }

    if (!ACTIONS[resolvedAction]) {
      return NextResponse.json({ error: `Unsupported action: ${resolvedAction}` }, { status: 400 });
    }

    const { dir, message } = await ACTIONS[resolvedAction]({ username, nationalId, userInfo, imageData });

    const imageFilename = imageName(username);
    const imagePath = dir ? path.join(dir, imageFilename) : null;

    return NextResponse.json({
      success: true,
      message,
      userInfo: {
        username,
        nationalId: nationalId || '', // May be empty for existing user actions
        name: userInfo?.name || '',
        department: userInfo?.department || '',
        government: userInfo?.government || '',
        status: resolvedAction,
        createdAt: new Date().toISOString(),
        image: imageFilename,
      },
      savedPath: imagePath,
    });
  } catch (error) {
    console.error("Error processing user action:", error);
    return NextResponse.json({ error: error.message || "Failed to process user" }, { status: 500 });
  }
}