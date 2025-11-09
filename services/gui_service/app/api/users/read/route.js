import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { verifyToken } from "../../../../lib/auth.js";
import { readUserDir } from "../../../../lib/readUserDir.js";

// Users data depends on filesystem and should not be cached
export const revalidate = 0;

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
    const token = authHeader?.replace('Bearer ', '');

    if (!token) return null;
    return verifyToken(token);
  } catch (error) {
    console.error('Auth error:', error);
    return null;
  }
}

// Map of known governments to their username prefixes (must match folder naming conventions)
const GOV_PREFIXES = {
  "Cairo": "ci",
  "Giza": "gz",
  "Alexandria": "ax",
  "Aswan": "an",
  "Luxor": "lx",
  "Kafr El Sheikh": "kh",
  "Minya": "mn",
  "Beheira": "bh",
  "Beni Suef": "bn",
  "Dakahlia": "dk",
  "Damietta": "dm",
  "Fayoum": "fj",
  "Gharbia": "ga",
  "Ismailia": "im",
  "Monufia": "mo",
  "Matrouh": "mt",
  "North Sinai": "ns",
  "Port Said": "pr",
  "Qalyubia": "ql",
  "Qena": "qn",
  "Red Sea": "rd",
  "Sohag": "sh",
  "South Sinai": "ss",
  "Sharqia": "sr",
  "Suez": "sz",
  "Asyut": "au"
};

function governmentToPrefix(gov) {
  if (!gov) return "";
  if (GOV_PREFIXES[gov]) return GOV_PREFIXES[gov];
  // Fallback: first two characters lowercased
  return String(gov).slice(0, 2).toLowerCase();
}

function getPrefixFromUsername(username) {
  return typeof username === 'string' ? username.substring(0, 2).toLowerCase() : '';
}

function buildAllowedGovFilters(authUser) {
  if (!authUser || authUser.role === 'main-admin') {
    return { bypass: true, allowedGovsLC: new Set(), allowedPrefixes: new Set() };
  }
  const governments = Array.isArray(authUser.governments) ? authUser.governments : [];
  const allowedGovsLC = new Set(governments.map(g => String(g).toLowerCase()));
  const allowedPrefixes = new Set(governments.map(governmentToPrefix));
  return { bypass: false, allowedGovsLC, allowedPrefixes };
}

function userMatchesAllowedGov(user, filters) {
  if (filters.bypass) return true;
  if (!user) return false;

  // Prefer explicit government on user object
  if (user.government) {
    const govLC = String(user.government).toLowerCase();
    if (filters.allowedGovsLC.has(govLC)) return true;
  }

  // Fallback to username prefix
  if (user.username) {
    const prefix = getPrefixFromUsername(user.username);
    if (filters.allowedPrefixes.has(prefix)) return true;
  }

  return false;
}

function filterUsersByAllowedGov(users, filters) {
  if (filters.bypass) return users;
  if (!Array.isArray(users)) return [];
  return users.filter(u => userMatchesAllowedGov(u, filters));
}

// End-user approval workflow: GET returns all users by status (pending/approved/blocked) with pagination
export async function GET(request) {
  try {
    // Check authentication and permissions for viewing stats
    const authenticatedUser = getAuthenticatedUser(request);
    if (!authenticatedUser) {
      return NextResponse.json({ success: false, error: "Authentication required" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get("status") || "all";
    const search = searchParams.get("search");
    const searchFields = searchParams.get("searchFields") || "username,nationalId,name,department,government";

    // Pagination parameters
    const page = parseInt(searchParams.get("page")) || 1;
    const limit = parseInt(searchParams.get("limit")) || 20;
    const isPaginated = searchParams.get("paginated") === "true";

    // Validate pagination parameters
    if (page < 1) {
      return NextResponse.json({ success: false, error: "Page must be greater than 0" }, { status: 400 });
    }
    if (limit < 1 || limit > 100) {
      return NextResponse.json({ success: false, error: "Limit must be between 1 and 100" }, { status: 400 });
    }

    const dataDir = path.join(process.env.GUI_DATA);

    if (!fs.existsSync(dataDir)) {
      const emptyResponse = {
        success: true,
        data: isPaginated ? {
          [status === "all" ? "all" : status]: {
            users: [],
            pagination: {
              currentPage: page,
              totalItems: 0,
              totalPages: 0,
              itemsPerPage: limit,
              hasNextPage: false,
              hasPreviousPage: false
            }
          }
        } : {
          pending: [],
          approved: [],
          rejected: [],
        },
      };
      return NextResponse.json(emptyResponse);
    }

    // Directory paths
    const statusDirApproved = path.join(process.env.USERDATABASE);
    const statusDirPending = path.join(process.env.GUI_DATA, "pending");
    const statusDirRejected = path.join(process.env.GUI_DATA, "rejected");

    let responseData;

    // Helper function to apply search filter to users
    const applySearchFilter = (users, searchTerm) => {
      if (!searchTerm || !searchTerm.trim()) return users;

      const normalizedSearch = searchTerm.toLowerCase();
      const searchFieldsArray = searchFields.split(',').map(f => f.trim());

      return users.filter(user => {
        return searchFieldsArray.some(field => {
          const value = user[field];
          if (!value) return false;
          return String(value).toLowerCase().includes(normalizedSearch);
        });
      });
    };

    // Build allowed governments filter for the current user
    const govFilters = buildAllowedGovFilters(authenticatedUser);

    if (isPaginated) {
      // Paginated response after filtering by allowed governments (and optionally search)
      const paginate = (allUsers) => {
        const totalItems = allUsers.length;
        const totalPages = Math.ceil(totalItems / limit);
        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        return {
          users: allUsers.slice(startIndex, endIndex),
          pagination: {
            currentPage: page,
            totalItems,
            totalPages,
            itemsPerPage: limit,
            hasNextPage: endIndex < totalItems,
            hasPreviousPage: page > 1
          }
        };
      };

      switch (status) {
        case "pending": {
          const allPending = readUserDir(statusDirPending);
          const filteredPendingByGov = filterUsersByAllowedGov(allPending, govFilters);
          const filteredPending = search ? applySearchFilter(filteredPendingByGov, search) : filteredPendingByGov;
          responseData = { pending: paginate(filteredPending) };
          break;
        }
        case "approved": {
          const allApproved = readUserDir(statusDirApproved);
          const filteredApprovedByGov = filterUsersByAllowedGov(allApproved, govFilters);
          const filteredApproved = search ? applySearchFilter(filteredApprovedByGov, search) : filteredApprovedByGov;
          responseData = { approved: paginate(filteredApproved) };
          break;
        }
        case "blocked":
        case "rejected": {
          const allRejected = readUserDir(statusDirRejected);
          const filteredRejectedByGov = filterUsersByAllowedGov(allRejected, govFilters);
          const filteredRejected = search ? applySearchFilter(filteredRejectedByGov, search) : filteredRejectedByGov;
          responseData = { rejected: paginate(filteredRejected) };
          break;
        }
        default: {
          const pendingAll = readUserDir(statusDirPending);
          const approvedAll = readUserDir(statusDirApproved);
          const rejectedAll = readUserDir(statusDirRejected);

          const pendingGov = filterUsersByAllowedGov(pendingAll, govFilters);
          const approvedGov = filterUsersByAllowedGov(approvedAll, govFilters);
          const rejectedGov = filterUsersByAllowedGov(rejectedAll, govFilters);

          const pendingFiltered = search ? applySearchFilter(pendingGov, search) : pendingGov;
          const approvedFiltered = search ? applySearchFilter(approvedGov, search) : approvedGov;
          const rejectedFiltered = search ? applySearchFilter(rejectedGov, search) : rejectedGov;

          responseData = {
            pending: paginate(pendingFiltered),
            approved: paginate(approvedFiltered),
            rejected: paginate(rejectedFiltered),
          };
        }
      }
    } else {
      // Legacy non-paginated response for backward compatibility
      let approvedUsers = readUserDir(statusDirApproved);
      let pendingUsers = readUserDir(statusDirPending);
      let blockedUsers = readUserDir(statusDirRejected);

      // First filter by allowed governments
      approvedUsers = filterUsersByAllowedGov(approvedUsers, govFilters);
      pendingUsers = filterUsersByAllowedGov(pendingUsers, govFilters);
      blockedUsers = filterUsersByAllowedGov(blockedUsers, govFilters);

      // Apply search filter if provided
      if (search) {
        approvedUsers = applySearchFilter(approvedUsers, search);
        pendingUsers = applySearchFilter(pendingUsers, search);
        blockedUsers = applySearchFilter(blockedUsers, search);
      }

      switch (status) {
        case "pending":
          responseData = { pending: pendingUsers };
          break;
        case "approved":
          responseData = { approved: approvedUsers };
          break;
        case "blocked":
        case "rejected":
          responseData = { rejected: blockedUsers };
          break;
        default:
          responseData = {
            pending: pendingUsers,
            approved: approvedUsers,
            rejected: blockedUsers,
          };
      }
    }

    return NextResponse.json({
      success: true,
      data: responseData,
    });
  } catch (error) {
    console.error("Error reading user data:", error);
    return NextResponse.json(
      { error: "Failed to read user data" },
      { status: 500 },
    );
  }
}
