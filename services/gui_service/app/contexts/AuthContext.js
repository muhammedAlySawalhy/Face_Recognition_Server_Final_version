'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(0);
  const router = useRouter();

  // Always check auth status on mount and whenever the token changes
  useEffect(() => {
    console.log("mounted")
    checkAuthStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      console.log('[DEBUG] checkAuthStatus: token from localStorage:', token);

      if (!token) {
        console.log('[DEBUG] No token found, user not authenticated');
        setIsAuthenticated(false);
        setUser(null);
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/auth/verify', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await response.json();
      console.log('[DEBUG] checkAuthStatus: /api/auth/verify result:', result);

      if (result.success && result.isAuthenticated) {
        setIsAuthenticated(true);
        setUser(result.user); // user object with role and permissions
        localStorage.setItem('currentUser', JSON.stringify(result.user));
        console.log('[DEBUG] User authenticated with fresh permissions:', result.user); // Temporary debug log
      } else {
        console.log('[DEBUG] Authentication failed, clearing tokens');
        setIsAuthenticated(false);
        setUser(null);
        localStorage.removeItem('adminToken');
        localStorage.removeItem('currentUser');
      }
    } catch (error) {
      console.error('Auth check error:', error);
      setIsAuthenticated(false);
      setUser(null);
      localStorage.removeItem('adminToken');
      localStorage.removeItem('currentUser');
    } finally {
      setIsLoading(false);
    }
  };
  const login = async (username, password) => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (result.success) {
        if (result.token) {
          localStorage.setItem('adminToken', result.token);
          console.log('[DEBUG] login: set new adminToken in localStorage:', result.token);
        } else {
          console.log('[DEBUG] login: no token returned from login');
        }
        // Store user data in localStorage
        if (result.user) {
          const permissions = Array.isArray(result.user.permissions) ? result.user.permissions : [];
          const governments = Array.isArray(result.user.governments) ? result.user.governments : [];

          localStorage.setItem('currentUser', JSON.stringify({
            ...result.user,
            permissions,
            governments
          }));
        }

        // Update state
        setIsAuthenticated(true);
        setUser(result.user);

        return { success: true, message: result.message };
      } else {
        throw new Error(result.error || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: error.message };
    }
  };



  const logout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    // Clear local storage and state
    localStorage.removeItem('adminToken');
    localStorage.removeItem('currentUser');
    setIsAuthenticated(false);
    setUser(null);
    router.push('/admin/login');
  };

  const hasPermission = (permission) => {
    // If not authenticated or no user, deny access immediately
    if (!isAuthenticated || !user) {
      console.log(`❌ Permission denied - no auth/user: ${permission}`);
      return false;
    }

    // Ensure user object has required properties
    if (!user.role || !user.permissions) {
      console.log(`❌ Permission denied - invalid user object: ${permission}`);
      return false;
    }

    // Main admin has all permissions
    if (user.role === 'main-admin') {
      console.log(`✅ Permission granted - main admin: ${permission}`);
      return true;
    }

    // Check if user has wildcard permission or the specific permission
    if (Array.isArray(user.permissions)) {
      if (user.permissions.includes('*') || user.permissions.includes(permission)) {
        console.log(`✅ Permission granted - explicit permission: ${permission}`);
        return true;
      }
    }

    console.log(`❌ Permission denied - insufficient permissions: ${permission}`, {
      userRole: user.role,
      userPermissions: user.permissions,
      requestedPermission: permission
    });
    return false;
  };

  const hasTabPermission = (tabPermission) => {
    // If not authenticated or no user, deny access immediately
    if (!isAuthenticated || !user) {
      console.log(`❌ Tab permission denied - no auth/user: ${tabPermission}`);
      return false;
    }

    // Ensure user object has required properties
    if (!user.role) {
      console.log(`❌ Tab permission denied - invalid user object: ${tabPermission}`);
      return false;
    }

    // Main admin has all tab permissions
    if (user.role === 'main-admin') {
      console.log(`✅ Tab permission granted - main admin: ${tabPermission}`);
      return true;
    }

    // Check if user has explicit tab permission
    if (Array.isArray(user.tabPermissions)) {
      if (user.tabPermissions.includes(tabPermission)) {
        console.log(`✅ Tab permission granted - explicit tab permission: ${tabPermission}`);
        return true;
      }
    }

    console.log(`❌ Tab permission denied - insufficient tab permissions: ${tabPermission}`, {
      userRole: user.role,
      userTabPermissions: user.tabPermissions,
      requestedTabPermission: tabPermission
    });
    return false;
  };

  const requireAuth = () => {
    if (!isAuthenticated) {
      router.push('/admin/login');
      return false;
    }
    return true;
  };

  const refreshUser = async (force = false) => {
    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setIsAuthenticated(false);
        setUser(null);
        return false;
      }

      // Call refresh endpoint to get updated token with current user data
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await response.json();
      if (result.success && result.user) {
        // Update localStorage with new token
        if (result.token) {
          localStorage.setItem('adminToken', result.token);
        }
        setUser(result.user);
        setLastRefresh(Date.now());
        console.log('User permissions refreshed:', result.user);
        return true;
      } else {
        // Token is invalid or user lost permissions, logout immediately
        console.log('User lost authentication/permissions, logging out');
        setIsAuthenticated(false);
        setUser(null);
        localStorage.removeItem('adminToken');
        localStorage.removeItem('currentUser');
        router.push('/admin/login');
        return false;
      }
    } catch (error) {
      console.error('Refresh user error:', error);
      // On error, assume no permissions for security
      setIsAuthenticated(false);
      setUser(null);
      return false;
    }
  };

  const value = {
    isAuthenticated,
    isLoading,
    user,
    login,
    logout,
    checkAuthStatus,
    hasPermission,
    hasTabPermission,
    requireAuth,
    refreshUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

function ProtectedRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/admin/login");
      } else if (requireAdmin && user && !user.role) {
        router.push("/admin/login");
      }
    }
  }, [isAuthenticated, isLoading, requireAdmin, user, router]);

  if (isLoading) {
    return <Loading message="Checking authentication..." minHeight="100vh" />;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}

export default AuthContext;