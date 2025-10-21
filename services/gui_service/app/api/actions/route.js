import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// This endpoint reads from filesystem and should not be cached
export const revalidate = 0;

// Helper to parse action filename
function parseActionFilename(filename) {
    // Example: 10_07_2025-14_44___Lock_screen___Wrong_user.jpg
    const parts = filename.split("___");
    if (parts.length < 3) return null;
    const [datePart, actionType, descriptionWithExt] = parts;
    const description = descriptionWithExt.replace(/\.jpg$/i, "");
    return {
        date: datePart.replace(/_/g, "/"),
        actionType,
        description,
    };
}

// Helper to read actions from a folder
function readActionsFromFolder(folderPath, actionType) {
    if (!fs.existsSync(folderPath)) return [];
    const clientFolders = fs.readdirSync(folderPath, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name);
    let actions = [];
    for (const clientName of clientFolders) {
        const clientPath = path.join(folderPath, clientName);
        const files = fs.readdirSync(clientPath).filter(f => f.endsWith(".jpg"));
        for (const file of files) {
            const meta = parseActionFilename(file);
            if (!meta || !meta.date) {
                console.warn('Skipping file with invalid format:', file);
                continue;
            }
            // Determine the correct base path from env
            let basePath = process.env.Actions;
            // The relative path from basePath to the image
            const relPath = path.relative(basePath, clientPath);
            // Use clientName as username param, relPath as path, image filename is not used as username
            actions.push({
                clientName,
                actionType,
                imageUrl: `/api/user-photo?username=${encodeURIComponent(clientName)}&base=${encodeURIComponent(basePath)}&path=${encodeURIComponent(relPath)}&file=${encodeURIComponent(file)}`,
                ...meta,
            });
        }
    }
    return actions;
}

export async function GET(request) {
    try {
        const { searchParams } = new URL(request.url);
        const page = parseInt(searchParams.get("page") || "0", 10);
        const pageSize = parseInt(searchParams.get("pageSize") || "10", 10);
        const groupBy = searchParams.get("groupBy"); // New parameter for grouping

        // Get server action paths from env
        const actionPaths = process.env.Actions || "/app/actions";
        let actions = [];
        // More robust validation
        if (!actionPaths || !actionPaths.trim()) {
            return NextResponse.json(
                { error: "No action paths configured" },
                { status: 400 }
            );
        }
        // Validate that the base directory exists
        if (!fs.existsSync(actionPaths)) {
            return NextResponse.json(
                { error: "Configured action path does not exist" },
                { status: 500 }
            );
        }
        try {
            const lockScreenDir = path.join(actionPaths, "Lock_screen");
            const signOutDir = path.join(actionPaths, "Sign_out");

            actions.push(...readActionsFromFolder(lockScreenDir, "Lock_screen"));
            actions.push(...readActionsFromFolder(signOutDir, "Sign_out"));
        } catch (error) {
            console.error("Error reading action folders:", error);
            return NextResponse.json(
                { error: "Failed to read action directories" },
                { status: 500 }
            );
        }


        // Sort by date descending (assuming date is in format DD_MM_YYYY-HH_MM)
        actions.sort((a, b) => b.date.localeCompare(a.date));

        if (groupBy === "username") {
            // Group actions by username
            const groupedActions = {};
            actions.forEach(action => {
                const uname = action.clientName || "";
                if (!groupedActions[uname]) {
                    groupedActions[uname] = [];
                }
                groupedActions[uname].push(action);
            });

            // Convert to array of usernames with their actions
            const usernames = Object.keys(groupedActions);
            const paginatedUsernames = usernames.slice(page * pageSize, (page + 1) * pageSize);

            const result = paginatedUsernames.map(username => ({
                username,
                actions: groupedActions[username],
                actionCount: groupedActions[username].length
            }));

            return NextResponse.json({
                data: result,
                pagination: {
                    page,
                    pageSize,
                    totalUsers: usernames.length,
                    totalActions: actions.length,
                    hasMore: (page + 1) * pageSize < usernames.length
                }
            });
        } else if (groupBy === "user-day") {
            // Group actions by username, then by day within each user
            const groupedByUser = {};
            actions.forEach(action => {
                const uname = action.clientName || "";
                if (!groupedByUser[uname]) {
                    groupedByUser[uname] = {};
                }

                // Extract date part only (without time) - handle undefined dates
                if (!action.date) {
                    console.warn('Action missing date:', action);
                    return; // Skip actions without dates
                }

                const dateOnly = action.date.split('-')[0]; // DD/MM/YYYY
                if (!dateOnly) {
                    console.warn('Invalid date format:', action.date);
                    return; // Skip actions with invalid date format
                }

                if (!groupedByUser[uname][dateOnly]) {
                    groupedByUser[uname][dateOnly] = [];
                }
                groupedByUser[uname][dateOnly].push(action);
            });

            // Convert to array format with day grouping within each user
            const usernames = Object.keys(groupedByUser);
            const paginatedUsernames = usernames.slice(page * pageSize, (page + 1) * pageSize);

            const result = paginatedUsernames.map(username => {
                const userDays = groupedByUser[username];
                const dates = Object.keys(userDays).sort((a, b) => {
                    // Convert DD/MM/YYYY to Date for proper sorting
                    const [dayA, monthA, yearA] = a.split('/');
                    const [dayB, monthB, yearB] = b.split('/');
                    const dateA = new Date(yearA, monthA - 1, dayA);
                    const dateB = new Date(yearB, monthB - 1, dayB);
                    return dateB - dateA; // Most recent first
                });

                const dayGroups = dates.map(date => ({
                    date,
                    actions: userDays[date],
                    actionCount: userDays[date].length
                }));

                const totalActions = dates.reduce((sum, date) => sum + userDays[date].length, 0);

                return {
                    username,
                    dayGroups,
                    actionCount: totalActions,
                    dayCount: dates.length
                };
            });

            return NextResponse.json({
                data: result,
                pagination: {
                    page,
                    pageSize,
                    totalUsers: usernames.length,
                    totalActions: actions.length,
                    hasMore: (page + 1) * pageSize < usernames.length
                }
            });
        } else if (groupBy === "day") {
            // Group actions by day
            const groupedActions = {};
            actions.forEach(action => {
                // Extract date part only (without time) - handle undefined dates
                if (!action.date) {
                    console.warn('Action missing date:', action);
                    return; // Skip actions without dates
                }

                const dateOnly = action.date.split('-')[0]; // DD/MM/YYYY
                if (!dateOnly) {
                    console.warn('Invalid date format:', action.date);
                    return; // Skip actions with invalid date format
                }

                if (!groupedActions[dateOnly]) {
                    groupedActions[dateOnly] = [];
                }
                groupedActions[dateOnly].push(action);
            });

            // Convert to array sorted by date (most recent first)
            const dates = Object.keys(groupedActions).sort((a, b) => {
                // Convert DD/MM/YYYY to Date for proper sorting
                const [dayA, monthA, yearA] = a.split('/');
                const [dayB, monthB, yearB] = b.split('/');
                const dateA = new Date(yearA, monthA - 1, dayA);
                const dateB = new Date(yearB, monthB - 1, dayB);
                return dateB - dateA; // Most recent first
            });

            const paginatedDates = dates.slice(page * pageSize, (page + 1) * pageSize);

            const result = paginatedDates.map(date => ({
                date,
                actions: groupedActions[date],
                actionCount: groupedActions[date].length
            }));

            return NextResponse.json({
                data: result,
                pagination: {
                    page,
                    pageSize,
                    totalDays: dates.length,
                    totalActions: actions.length,
                    hasMore: (page + 1) * pageSize < dates.length
                }
            });
        } else {
            // Original pagination by individual actions
            const paged = actions.slice(page * pageSize, (page + 1) * pageSize);
            return NextResponse.json(paged);
        }
    } catch (error) {
        console.error("Error reading actions:", error);
        return NextResponse.json([], { status: 500 });
    }
}
