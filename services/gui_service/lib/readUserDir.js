import fs from "fs";
import path from "path";

/**
 * Read user data from the new directory structure with pagination support.
 * 
 * Reads all users in a given status directory (approved, blocked, pending)
 * and returns an array of user objects with their info and image path.
 * 
 * @param {string} statusDir - Absolute path to the status directory (e.g., `${USERDATABASE}/approved`)
 * @param {Object} options - Optional pagination and filtering options
 * @param {number} options.page - Page number (1-based)
 * @param {number} options.limit - Number of items per page
 * @param {boolean} options.paginated - Whether to return paginated results
 * @returns {Array|Object} - Array of user data objects or paginated result object
 */
export const readUserDir = (statusDir, options = {}) => {
    if (!fs.existsSync(statusDir)) {
        if (options.paginated) {
            return {
                users: [],
                pagination: {
                    currentPage: options.page || 1,
                    totalItems: 0,
                    totalPages: 0,
                    itemsPerPage: options.limit || 20,
                    hasNextPage: false,
                    hasPreviousPage: false
                }
            };
        }
        return [];
    }

    // System folders to exclude (these are not user folders)
    const systemFolders = ['pending', 'blocked', 'approved', 'temp', 'backup', 'logs'];

    // Get all user directories
    const userDirs = fs.readdirSync(statusDir, { withFileTypes: true })
        .filter(dirent => dirent.isDirectory())
        .map(dirent => dirent.name)
        .filter(name => !systemFolders.includes(name.toLowerCase())); // Filter out system folders

    // If pagination is requested, calculate pagination info
    if (options.paginated) {
        const page = options.page || 1;
        const limit = options.limit || 20;
        const totalItems = userDirs.length;
        const totalPages = Math.ceil(totalItems / limit);
        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;

        // Only process the directories we need for this page
        const paginatedDirs = userDirs.slice(startIndex, endIndex);
        const users = processUserDirectories(statusDir, paginatedDirs);

        return {
            users,
            pagination: {
                currentPage: page,
                totalItems,
                totalPages,
                itemsPerPage: limit,
                hasNextPage: endIndex < totalItems,
                hasPreviousPage: page > 1
            }
        };
    }

    // For non-paginated requests, process all directories
    return processUserDirectories(statusDir, userDirs);
};

/**
 * Process user directories and extract user information
 * @param {string} statusDir - Base status directory path
 * @param {Array} userDirs - Array of user directory names to process
 * @returns {Array} - Array of user data objects
 */
function processUserDirectories(statusDir, userDirs) {
    const users = [];

    for (const username of userDirs) {
        const userFolder = path.join(statusDir, username);
        const infoPath = path.join(userFolder, "info.json");
        const imagePath = path.join(userFolder, `${username}_1.jpg`);
        let userInfo = { username };

        // Try to read user info from info.json if exists
        if (fs.existsSync(infoPath)) {
            try {
                userInfo = {
                    ...userInfo,
                    ...JSON.parse(fs.readFileSync(infoPath, "utf8"))
                };
            } catch (e) {
                // fallback: continue with just username
            }
        }
        else {
            // If info.json doesn't exist, create a basic structure
            if (process.env.USERDATABASE === statusDir) {
                userInfo = {
                    ...userInfo,
                    status: "approved" // Default status if no info.json
                };
            }
            else {
                const statusType = path.basename(statusDir).toLowerCase();
                userInfo = { ...userInfo, status: statusType };
            }
        }

        // Attach image path if the image exists
        if (fs.existsSync(imagePath)) {
            userInfo.image = imagePath;
        }

        users.push(userInfo);
    }

    return users;
}