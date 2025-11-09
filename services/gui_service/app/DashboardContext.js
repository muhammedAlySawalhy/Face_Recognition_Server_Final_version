import React, { createContext, useState, useCallback, useEffect, useRef, useContext, useMemo } from "react";
import { useRuntimeEnv } from "./contexts/RuntimeEnvContext";

// ------------------- Helper Functions -------------------

function getCurrentAdmin() {
  try {
    const admin = localStorage.getItem("currentUser");
    if (!admin) return null;
    const parsed = JSON.parse(admin);
    if (parsed.governments && Array.isArray(parsed.governments)) {
      return parsed;
    } else if (parsed.government) {
      parsed.governments = [parsed.government];
      return parsed;
    } else {
      parsed.governments = [];
      return parsed;
    }
  } catch (e) {
    console.error("Error parsing currentUser from localStorage:", e);
    return null;
  }
}

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
  return gov.slice(0, 2).toLowerCase();
}

function getGovernmentFromUsername(username) {
  return typeof username === "string" ? username.substring(0, 2).toLowerCase() : "";
}

function filterByGovernment(clients, adminGovPrefixes) {
  return clients.filter(
    client =>
      client.username &&
      adminGovPrefixes.includes(getGovernmentFromUsername(client.username))
  );
}

function normalizeClients(clients) {
  if (!Array.isArray(clients)) return [];
  return clients.map(client => {
    if (typeof client === "string") {
      let username = client;
      if (
        username.length > 2 &&
        ((username.startsWith('"') && username.endsWith('"')) ||
          (username.startsWith("'") && username.endsWith("'")))
      ) {
        username = username.slice(1, -1);
      }
      return { username };
    }
    if (client && typeof client === "object" && client.username) {
      return client;
    }
    return { username: String(client) };
  });
}

function mergeArrays(arrays) {
  const flat = arrays.flat();
  if (!flat.length) return [];
  if (flat[0]?.username) {
    const map = new Map();
    flat.forEach(u => map.set(u.username, { ...map.get(u.username), ...u }));
    return Array.from(map.values());
  }
  if (flat[0]?.id) {
    const map = new Map();
    flat.forEach(n => map.set(n.id, { ...map.get(n.id), ...n }));
    return Array.from(map.values()).sort((a, b) => new Date(b.time) - new Date(a.time));
  }
  return flat;
}

function diffClients(prev, next) {
  const prevSet = new Set((prev || []).map(u => u.username));
  const nextSet = new Set((next || []).map(u => u.username));
  const added = [...nextSet].filter(u => !prevSet.has(u));
  return { added };
}

// Regex to match any possible shape for national id
const NATIONAL_ID_REGEX = /^(national[\s_-]?id|nat[\s_-]?id|nationalid|nationalID|nationalId|natid|natID|nId)$/i;

// Finds the national ID key in an object
function getNationalIdField(userObj) {
  for (const key in userObj) {
    if (NATIONAL_ID_REGEX.test(key)) {
      return userObj[key];
    }
  }
  return null;
}

// ------------------- END Helper Functions -------------------

const KEYS = [
  "active_clients",
  "deactivate_clients",
  "paused_clients",
  "blocked_clients",
  "connecting_internet_error"
];

export const DashboardContext = createContext();

// New smaller contexts
export const LiveClientsContext = createContext();
export const UsersDataContext = createContext();
export const NotificationsContext = createContext();
export const LookupContext = createContext();

export function DashboardProvider({ children }) {
  // Use runtime environment variables
  const config = useRuntimeEnv();

  // Load approved users from UserDB instead of Excel
  const [approvedUsers, setApprovedUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [rejectedUsers, setRejectedUsers] = useState([]);
  useEffect(() => {
    async function allUsers() {
      try {
        const token = localStorage.getItem('adminToken');
        if (!token) {
          console.error('No admin token found');
          setApprovedUsers([]);
          return;
        }

        const res = await fetch('/api/users/read?staus=all&&paginated=false', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });


        if (!res.ok) {
          console.error('Failed to fetch approved users:', res.status, res.statusText);
          setApprovedUsers([]);
          return;
        }

        const response = await res.json();
        console.log('Response from UserDB:', response);

        if (response.success && response.data.approved) {
          console.log('Successfully loaded approved users from UserDB:', response.data.approved);
          setApprovedUsers(response.data.approved);
          setPendingUsers(response.data.pending || []);
          setRejectedUsers(response.data.rejected || []);
          // If you need to log the updated state, use a separate useEffect
          // or log the data directly before setting it
          console.log('Setting approved users in state:', response.data.approved);
        } else {
          console.error('Approved users fetch failed:', response.error || 'Unknown error');
          setApprovedUsers([]);
          setPendingUsers([]);
          setRejectedUsers([]);
        }
      } catch (error) {
        console.error('Error loading approved users:', error);
        setApprovedUsers([]);
        setPendingUsers([]);
        setRejectedUsers([]);
      }
    }

    allUsers();
  }, []);



  const [data, setData] = useState({
    active: [],
    deactivated: [],
    pause: [],
    blocked: [],
    connectingError: [],
    users: [],
    notifications: [],
    userMap: {},
    nationalIdMap: {}
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const fetchTimeoutRef = useRef(null);

  const prevActive = useRef([]);
  const prevDeactivated = useRef([]);

  const fetchDashboardData = useCallback(async () => {
    if (loading) return;

    setLoading(true);
    setError(false);

    try {
      const token = localStorage.getItem('adminToken');
      const res = await fetch('/api/multi/redis/get', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ keys: KEYS })
      });

      if (!res.ok) throw new Error(`Forward route error ${res.status}`);
      const resp = await res.json();

      const serverPayloads = [resp?.s1?.data, resp?.s2?.data].filter(Boolean);
      if (serverPayloads.length === 0) {
        setError(true);
        setData({
          active: [],
          deactivated: [],
          pause: [],
          blocked: [],
          connectingError: [],
          users: [],
          notifications: [],
          userMap: {},
          nationalIdMap: {},
        });
      } else {
        const parse = v => {
          try { return typeof v === 'string' ? JSON.parse(v) : v; } catch { return v; }
        };
        const extractDataArray = (payload) => {
          const p = parse(payload);
          if (Array.isArray(p)) return p;
          if (p && Array.isArray(p.data)) return p.data;
          if (p && p.data && Array.isArray(p.data.data)) return p.data.data;
          return [];
        };

        const allArrays = serverPayloads.map(extractDataArray);

        const all = allArrays.map((dataArray) => {
          let active = [];
          let deactivated = [];
          let pause = [];
          let blocked = [];
          let connectingError = [];
          let users = [];

          dataArray.forEach(item => {
            if (item.active_clients) {
              active = active.concat(normalizeClients(parse(item.active_clients) || []));
            }
            if (item.deactivate_clients) {
              deactivated = deactivated.concat(normalizeClients(parse(item.deactivate_clients) || []));
            }
            if (item.paused_clients) {
              pause = pause.concat(normalizeClients(parse(item.paused_clients) || []));
            }
            if (item.blocked_clients) {
              blocked = blocked.concat(normalizeClients(parse(item.blocked_clients) || []));
            }
            if (item.connecting_internet_error) {
              connectingError = connectingError.concat(normalizeClients(parse(item.connecting_internet_error) || []));
            }
            if (item.users) {
              users = users.concat(normalizeClients(parse(item.users) || []));
            }
          });

          return { active, deactivated, pause, blocked, connectingError, users };
        });

        const currentAdmin = getCurrentAdmin();
        const adminGovPrefixes = (currentAdmin?.governments || []).map(governmentToPrefix);

        const mergedUsers = mergeArrays(all.map(a => a.users));
        const mergedActive = filterByGovernment(mergeArrays(all.map(a => a.active)), adminGovPrefixes);
        const mergedDeactivated = filterByGovernment(mergeArrays(all.map(a => a.deactivated)), adminGovPrefixes);

        // Create maps for fast lookup
        const userMap = {};
        const nationalIdMap = {};
        for (const user of mergedUsers) {
          if (user.username) userMap[user.username] = user;
          const nid = getNationalIdField(user);
          if (nid) nationalIdMap[nid] = user;
        }

        // Notifications
        const notifications = [...data.notifications];

        const { added: activeAdded } = diffClients(prevActive.current, mergedActive);
        activeAdded.forEach(username => {
          notifications.unshift({
            type: "activated",
            user: username,
            time: new Date().toLocaleString(),
            action: "became active"
          });
        });

        const { added: deactivatedAdded } = diffClients(prevDeactivated.current, mergedDeactivated);
        deactivatedAdded.forEach(username => {
          notifications.unshift({
            type: "deactivated",
            user: username,
            time: new Date().toLocaleString(),
            action: "became deactivated"
          });
        });

        while (notifications.length > 50) notifications.pop();

        prevActive.current = mergedActive;
        prevDeactivated.current = mergedDeactivated;

        setData({
          active: mergedActive,
          deactivated: mergedDeactivated,
          pause: mergeArrays(all.map(a => a.pause)),
          blocked: mergeArrays(all.map(a => a.blocked)),
          connectingError: filterByGovernment(mergeArrays(all.map(a => a.connectingError)), adminGovPrefixes),
          users: mergedUsers,
          notifications,
          userMap,
          nationalIdMap,
        });
      }
    } catch (e) {
      setError(true);
      setData({
        active: [],
        deactivated: [],
        pause: [],
        blocked: [],
        connectingError: [],
        users: [],
        notifications: [],
        userMap: {},
        nationalIdMap: {},
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  // Helper: Find user by national ID from approved users
  const findUserByNationalIdExcel = useCallback(async (nationalId) => {
    if (!nationalId) return null;
    // Convert both to string for comparison
    const res = await fetch('/api/excel-data')
    const data = await res.json();
    if (!data || !data.users) {
      console.error('No users found in Excel data');
      return null;
    }
    console.log(data, "data from excel path")
    const excelUsers = data?.users || [];
    console.log(excelUsers, "excel users from excel path")
    return excelUsers.find(u => String(u.nationalId) === String(nationalId)) || null;
  }, []);
  const findUserByNationalId = useCallback((nationalId) => {
    if (!nationalId) return null;
    // Convert both to string for comparison
    console.log(approvedUsers, "approved users from UserDB")
    return approvedUsers.find(u => String(u.nationalId) === String(nationalId)) || null;
  }, [approvedUsers]);

  // Helper: Find user by username in approved users
  const findUserByUsername = useCallback((username) => {
    if (!username) return null;
    return approvedUsers.find(u => String(u.username).toLowerCase() === String(username).toLowerCase()) || null;
  }, [approvedUsers]);

  // Helper: Search users by multiple criteria (username, nationalId, name) in approved users
  const searchUsers = useCallback((query) => {
    if (!query || !query.trim()) {
      // Return all approved users when no query is provided
      return approvedUsers;
    }
    const searchTerm = query.trim().toLowerCase();

    return approvedUsers.filter(user => {
      const username = String(user.username || '').toLowerCase();
      const nationalId = String(user.nationalId || '').toLowerCase();
      const name = String(user.name || '').toLowerCase();
      const department = String(user.department || '').toLowerCase();
      const government = String(user.government || '').toLowerCase();

      return username.includes(searchTerm) ||
        nationalId.includes(searchTerm) ||
        name.includes(searchTerm) ||
        department.includes(searchTerm) ||
        government.includes(searchTerm);
    });
  }, [approvedUsers]);

  // Helper: Find user by National ID and enhance with stored user data (already approved)
  const findUserByNationalIdEnhanced = useCallback(async (nationalId) => {
    if (!nationalId) return null;

    // Find the user in approved users from UserDB
    const approvedUser = approvedUsers.find(u => String(u.nationalId) === String(nationalId));

    if (!approvedUser) {
      // If not found in approved users, user doesn't exist in system yet
      return null;
    }

    // User is already approved, return with enhanced data
    return {
      ...approvedUser,
      hasStoredData: true,
      status: 'approved' // Ensure status is set to approved
    };
  }, [approvedUsers]);

  // Helper: Find user by username and enhance with stored data (already approved)
  const findUserByUsernameEnhanced = useCallback(async (username) => {
    if (!username) return null;

    // Find the user in approved users from UserDB
    const approvedUser = approvedUsers.find(u => String(u.username).toLowerCase() === String(username).toLowerCase());

    if (!approvedUser) {
      // If not found in approved users, user doesn't exist in system yet
      return null;
    }

    // User is already approved, return with enhanced data
    return {
      ...approvedUser,
      hasStoredData: true,
      status: 'approved' // Ensure status is set to approved
    };
  }, [approvedUsers]);

  // Memoized slices for small contexts to avoid unnecessary re-renders
  const liveClientsValue = useMemo(() => ({
    active: data.active,
    deactivated: data.deactivated,
    pause: data.pause,
    blocked: data.blocked,
    connectingError: data.connectingError,
    loading,
    error,
    fetchDashboardData,
  }), [data.active, data.deactivated, data.pause, data.blocked, data.connectingError, loading, error, fetchDashboardData]);

  const usersDataValue = useMemo(() => ({
    approvedUsers,
    pendingUsers,
    rejectedUsers,
  }), [approvedUsers, rejectedUsers, pendingUsers]);

  const notificationsValue = useMemo(() => ({
    notifications: data.notifications,
  }), [data.notifications]);

  const lookupValue = useMemo(() => ({
    findUserByNationalId,
    findUserByNationalIdExcel,
    findUserByUsername,
    findUserByNationalIdEnhanced,
    findUserByUsernameEnhanced,
    searchUsers,
    userMap: data.userMap,
    nationalIdMap: data.nationalIdMap,
  }), [findUserByNationalIdExcel, findUserByNationalId, findUserByUsername, findUserByNationalIdEnhanced, findUserByUsernameEnhanced, searchUsers, data.userMap, data.nationalIdMap]);

  const bigContextValue = useMemo(() => ({
    ...data,
    loading,
    error,
    fetchDashboardData,
    findUserByNationalId,
    findUserByUsername,
    findUserByNationalIdEnhanced,
    findUserByUsernameEnhanced,
    findUserByNationalIdExcel,
    searchUsers,
    approvedUsers,
    pendingUsers,
    config
  }), [data, loading, error, findUserByNationalIdExcel, fetchDashboardData, findUserByNationalId, findUserByUsername, findUserByNationalIdEnhanced, findUserByUsernameEnhanced, searchUsers, approvedUsers, pendingUsers, config]);

  return (
    <DashboardContext.Provider value={bigContextValue}>
      <LiveClientsContext.Provider value={liveClientsValue}>
        <UsersDataContext.Provider value={usersDataValue}>
          <NotificationsContext.Provider value={notificationsValue}>
            <LookupContext.Provider value={lookupValue}>
              {children}
            </LookupContext.Provider>
          </NotificationsContext.Provider>
        </UsersDataContext.Provider>
      </LiveClientsContext.Provider>
    </DashboardContext.Provider>
  );
}

// Custom hook to use dashboard context (legacy, broad updates)
export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
}

// New fine-grained hooks
export function useLiveClients() {
  const ctx = useContext(LiveClientsContext);
  if (!ctx) throw new Error('useLiveClients must be used within a DashboardProvider');
  return ctx;
}

export function useUsersData() {
  const ctx = useContext(UsersDataContext);
  if (!ctx) throw new Error('useUsersData must be used within a DashboardProvider');
  return ctx;
}

export function useNotificationsData() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotificationsData must be used within a DashboardProvider');
  return ctx;
}

export function useUserLookup() {
  const ctx = useContext(LookupContext);
  if (!ctx) throw new Error('useUserLookup must be used within a DashboardProvider');
  return ctx;
}