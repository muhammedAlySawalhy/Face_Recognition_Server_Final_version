"use client";

import React, { useState, useEffect } from "react";
import { FiGrid, FiUserCheck, FiUsers, FiSettings, FiCamera, FiActivity } from "react-icons/fi";
import {
  Box,
  Button,
  Center,
  Flex,
  VStack,
  HStack,
  Text,
  useToast,
  Heading,
  Image,
  Card,
  CardBody,
  Badge,
  SimpleGrid,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Alert,
  AlertIcon,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Avatar,
  Input,
  Select,
  Checkbox,
  FormControl,
  FormLabel,
  Stack,
} from "@chakra-ui/react";
import { ChevronDownIcon } from "@chakra-ui/icons";
import { useRouter } from "next/navigation";
import Permission from "../components/Permission";
import { useAuth } from "../contexts/AuthContext";
import { useRuntimeEnv } from "../contexts/RuntimeEnvContext";
import { useUsersData, useLiveClients } from "../DashboardContext";

// User Management Functions
const UserManager = {
  // Get user by username
  getUserByUsername: (users, username) => {
    return users.find(u => u.username === username);
  },

  // Update user password
  updateUserPassword: async (username, newPassword) => {
    try {
      const response = await fetch('/api/users/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'update-password',
          user: { username, password: newPassword }
        })
      });
      return await response.json();
    } catch (error) {
      throw new Error('Failed to update password');
    }
  },

  // Check if user is main admin
  isMainAdmin: (user) => {
    return user && user.role === 'main-admin';
  },

  // Check if there's only one main admin
  validateSingleMainAdmin: (users, currentUsername = null) => {
    const mainAdmins = users.filter(u => u.role === 'main-admin');
    if (currentUsername) {
      // When updating, ensure we don't remove the last main admin
      const otherMainAdmins = mainAdmins.filter(u => u.username !== currentUsername);
      return otherMainAdmins.length > 0;
    }
    return mainAdmins.length === 1;
  },

  // Delete user
  deleteUser: async (username) => {
    try {
      const response = await fetch('/api/users/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'delete-user',
          user: { username }
        })
      });
      return await response.json();
    } catch (error) {
      throw new Error('Failed to delete user');
    }
  }
};

// Loading Component
function Loading({ message = "Loading...", minHeight = "200px" }) {
  return (
    <Center minH={minHeight}>
      <VStack>
        <Box
          borderRadius="full"
          border="4px solid #e2e8f0"
          borderTopColor="#3182ce"
          w="40px"
          h="40px"
          animation="spin 1s linear infinite"
        />
        <Text color="gray.500">{message}</Text>
      </VStack>
    </Center>
  );
}

// Admin Users Management GUI
function AdminUsersManager() {
  const { refreshUser, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [allPermissions, setAllPermissions] = useState([
    "approve_user",
    "block_user",
    "pause_user",
    "reject_user",
    "view_stats",
    "capture_photo",
    "add_user",
    "edit_user_permissions",
    "delete_user"
  ]);

  const [allTabPermissions, setAllTabPermissions] = useState([
    "tab_dashboard",
    "tab_available_users",
    "tab_users",
    "tab_actions",
    "tab_settings",
    "tab_take_photo"
  ]);

  // Password change state
  const [passwordChange, setPasswordChange] = useState({
    username: '',
    newPassword: '',
    confirmPassword: '',
    isVisible: false
  });

  // Delete confirmation state
  const [deleteConfirmation, setDeleteConfirmation] = useState({
    username: '',
    isVisible: false
  });

  const availableGovernments = [
    "Alexandria",
    "Aswan",
    "Asyut",
    "Beheira",
    "Beni Suef",
    "Cairo",
    "Dakahlia",
    "Damietta",
    "Fayoum",
    "Gharbia",
    "Giza",
    "Ismailia",
    "Kafr El Sheikh",
    "Luxor",
    "Matrouh",
    "Minya",
    "Monufia",
    "North Sinai",
    "Port Said",
    "Qalyubia",
    "Qena",
    "Red Sea",
    "Sharqia",
    "Sohag",
    "South Sinai",
    "Suez"
  ];
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'admin', permissions: [], tabPermissions: ['tab_settings'], governments: [] });
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const config = useRuntimeEnv();

  useEffect(() => {
    fetchAdmins();
  }, []);
  useEffect(() => {
    refreshUser();
  }, [])
  const fetchAdmins = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/users/manage');
      const data = await res.json();
      if (data.success) {
        // Transform users: remove prefixes from permissions, use governments directly
        const cleanUsers = (data.users || []).map(u => {
          const permissions = Array.isArray(u.permissions)
            ? Array.from(new Set(u.permissions.map(p => p.split('_').slice(1).join('_') || p)))
            : [];
          // Use governments directly from user object
          const governments = Array.isArray(u.governments) ? u.governments : [];
          return { ...u, permissions, governments };
        });
        setUsers(cleanUsers);
      }
    } catch (error) {
      return;
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    if (!newUser.username || !newUser.password) {
      toast({ title: 'Error', description: 'Username and password are required', status: 'error', duration: 3000 });
      return;
    }
    if (!newUser.governments || newUser.governments.length === 0) {
      toast({ title: 'Error', description: 'At least one government must be selected', status: 'error', duration: 3000 });
      return;
    }

    // Validate main-admin role restriction
    if (newUser.role === 'main-admin') {
      const hasMainAdmin = users.some(u => u.role === 'main-admin');
      if (hasMainAdmin) {
        toast({
          title: 'Error',
          description: 'Only one main admin is allowed. Please use admin role instead.',
          status: 'error',
          duration: 4000
        });
        return;
      }
    }

    setLoading(true);
    try {
      const res = await fetch('/api/users/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', user: newUser })
      });
      const data = await res.json();
      if (data.success) {
        toast({ title: 'Success', description: 'User created successfully', status: 'success', duration: 3000 });
        setNewUser({ username: '', password: '', role: 'admin', permissions: [], tabPermissions: ['tab_settings'], governments: [] });
        fetchAdmins();
      } else {
        toast({ title: 'Error', description: data.message || 'Failed to create user', status: 'error', duration: 3000 });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to create user', status: 'error', duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionChange = async (username, permission, checked) => {
    setLoading(true);
    try {
      const user = users.find(u => u.username === username);
      if (!user) return;
      let permissions = user.permissions || [];
      if (checked) {
        permissions = [...new Set([...permissions, permission])];
      } else {
        permissions = permissions.filter(p => p !== permission);
      }
      const res = await fetch('/api/users/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'update-permissions', user: { username, permissions } })
      });
      const data = await res.json();
      if (data.success) {
        toast({ title: 'Success', description: 'Permissions updated successfully', status: 'success', duration: 3000 });
        fetchAdmins();

        // If the current user's permissions were changed, refresh their auth data
        if (currentUser && currentUser.username === username) {
          await refreshUser(true); // Force refresh
          toast({
            title: 'Permissions Refreshed',
            description: 'Your permissions have been updated and will take effect immediately',
            status: 'info',
            duration: 3000
          });
        }
      } else {
        toast({ title: 'Error', description: data.message || 'Failed to update permissions', status: 'error', duration: 3000 });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update permissions', status: 'error', duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  const handleTabPermissionChange = async (username, tabPermission, checked) => {
    setLoading(true);
    try {
      const user = users.find(u => u.username === username);
      if (!user) return;
      let tabPermissions = user.tabPermissions || [];
      if (checked) {
        tabPermissions = [...new Set([...tabPermissions, tabPermission])];
      } else {
        tabPermissions = tabPermissions.filter(tp => tp !== tabPermission);
      }
      const res = await fetch('/api/users/manage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'update-tab-permissions', user: { username, tabPermissions } })
      });
      const data = await res.json();
      if (data.success) {
        toast({ title: 'Success', description: 'Tab permissions updated successfully', status: 'success', duration: 3000 });
        fetchAdmins();

        // If the current user's tab permissions were changed, refresh their auth data
        if (currentUser && currentUser.username === username) {
          await refreshUser(true); // Force refresh
          toast({
            title: 'Tab Permissions Refreshed',
            description: 'Your tab permissions have been updated and will take effect immediately',
            status: 'info',
            duration: 3000
          });
        }
      } else {
        toast({ title: 'Error', description: data.message || 'Failed to update tab permissions', status: 'error', duration: 3000 });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update tab permissions', status: 'error', duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  const handleNewUserPermissionChange = (permission, checked) => {
    setNewUser(prev => {
      let permissions = prev.permissions || [];
      if (checked) {
        permissions = [...new Set([...permissions, permission])];
      } else {
        permissions = permissions.filter(p => p !== permission);
      }
      return { ...prev, permissions };
    });
  };

  const handleNewUserTabPermissionChange = (tabPermission, checked) => {
    setNewUser(prev => {
      let tabPermissions = prev.tabPermissions || [];
      if (checked) {
        tabPermissions = [...new Set([...tabPermissions, tabPermission])];
      } else {
        tabPermissions = tabPermissions.filter(tp => tp !== tabPermission);
      }
      return { ...prev, tabPermissions };
    });
  };

  // Password change handlers
  const handlePasswordChange = async () => {
    if (!passwordChange.username || !passwordChange.newPassword) {
      toast({ title: 'Error', description: 'Username and password are required', status: 'error', duration: 3000 });
      return;
    }
    if (passwordChange.newPassword !== passwordChange.confirmPassword) {
      toast({ title: 'Error', description: 'Passwords do not match', status: 'error', duration: 3000 });
      return;
    }
    if (passwordChange.newPassword.length < 6) {
      toast({ title: 'Error', description: 'Password must be at least 6 characters', status: 'error', duration: 3000 });
      return;
    }

    setLoading(true);
    try {
      const result = await UserManager.updateUserPassword(passwordChange.username, passwordChange.newPassword);
      if (result.success) {
        toast({ title: 'Success', description: 'Password updated successfully', status: 'success', duration: 3000 });
        setPasswordChange({ username: '', newPassword: '', confirmPassword: '', isVisible: false });
      } else {
        toast({ title: 'Error', description: result.message || 'Failed to update password', status: 'error', duration: 3000 });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update password', status: 'error', duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  const showPasswordChangeForm = (username) => {
    setPasswordChange({ username, newPassword: '', confirmPassword: '', isVisible: true });
  };

  // Delete user handlers
  const showDeleteConfirmation = (username) => {
    setDeleteConfirmation({ username, isVisible: true });
  };

  const handleDeleteUser = async () => {
    if (!deleteConfirmation.username) return;

    // Prevent self-deletion
    if (deleteConfirmation.username === currentUser?.username) {
      toast({ title: 'Error', description: 'Cannot delete your own account', status: 'error', duration: 3000 });
      return;
    }

    setLoading(true);
    try {
      const result = await UserManager.deleteUser(deleteConfirmation.username);
      if (result.success) {
        toast({ title: 'Success', description: 'User deleted successfully', status: 'success', duration: 3000 });
        setDeleteConfirmation({ username: '', isVisible: false });
        fetchAdmins(); // Refresh the users list
      } else {
        toast({ title: 'Error', description: result.message || 'Failed to delete user', status: 'error', duration: 3000 });
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to delete user', status: 'error', duration: 3000 });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box mt={10} mb={10} p={6} bg="rgba(255,255,255,0.05)" borderRadius="2xl" boxShadow="0 8px 32px 0 rgba(31, 38, 135, 0.37)" border="1px solid rgba(255,255,255,0.18)" backdropFilter="blur(8px)">
      <Heading size="md" mb={4} color="#00E5FF">Admin Users Management</Heading>
      {/* Create Admin User */}
      <Box mb={6} p={4} bg="rgba(255,255,255,0.03)" borderRadius="md" border="1px solid rgba(255,255,255,0.1)">
        <Text fontWeight="bold" mb={4} color="#e0eaff">Create New Admin User</Text>
        <VStack spacing={4} align="stretch">
          <HStack spacing={3}>
            <FormControl>
              <FormLabel color="#7ecbff">Username</FormLabel>
              <Input
                placeholder="Enter username"
                value={newUser.username}
                onChange={e => setNewUser(prev => ({ ...prev, username: e.target.value }))}
                bg="rgba(255,255,255,0.1)"
                color="white"
                border="1px solid rgba(255,255,255,0.2)"
                _placeholder={{ color: "gray.400" }}
                _hover={{ borderColor: "#00E5FF" }}
                _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
              />
            </FormControl>
            <FormControl>
              <FormLabel color="#7ecbff">Password</FormLabel>
              <Input
                type="password"
                placeholder="Enter password"
                value={newUser.password}
                onChange={e => setNewUser(prev => ({ ...prev, password: e.target.value }))}
                bg="rgba(255,255,255,0.1)"
                color="white"
                border="1px solid rgba(255,255,255,0.2)"
                _placeholder={{ color: "gray.400" }}
                _hover={{ borderColor: "#00E5FF" }}
                _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
              />
            </FormControl>
            {/* <FormControl>
              <FormLabel color="#7ecbff">Role</FormLabel>
              <Select
                value={newUser.role}
                onChange={e => setNewUser(prev => ({ ...prev, role: e.target.value }))}
                bg="rgba(255,255,255,0.1)"
                color="white"
                border="1px solid rgba(255,255,255,0.2)"
                _hover={{ borderColor: "#00E5FF" }}
                _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
              >
                <option value="admin" style={{ backgroundColor: '#2D3748', color: 'white' }}>Admin</option>
                <option value="main-admin" style={{ backgroundColor: '#2D3748', color: 'white' }}>Main Admin</option>
              </Select>
              
            </FormControl> */}
            <FormControl>
              <FormLabel color="#7ecbff">Governments</FormLabel>
              <Box
                bg="rgba(255,255,255,0.05)"
                border="1px solid rgba(255,255,255,0.15)"
                borderRadius="md"
                p={4}
                maxH="200px"
                overflowY="auto"
                minW="300px"
              >
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={2}>
                  {availableGovernments.map(gov => (
                    <Checkbox
                      key={gov}
                      isChecked={newUser.governments?.includes(gov)}
                      onChange={e => {
                        const checked = e.target.checked;
                        setNewUser(prev => ({
                          ...prev,
                          governments: checked
                            ? [...(prev.governments || []), gov]
                            : (prev.governments || []).filter(g => g !== gov)
                        }));
                      }}
                      color="white"
                      size="sm"
                      colorScheme="cyan"
                    >
                      <Text fontSize="sm" color="white">{gov}</Text>
                    </Checkbox>
                  ))}
                </SimpleGrid>
                {newUser.governments?.length > 0 && (
                  <Box mt={3} pt={3} borderTop="1px solid rgba(255,255,255,0.15)">
                    <Text fontSize="xs" color="gray.400" mb={1}>
                      Selected ({newUser.governments.length}):
                    </Text>
                    <Text fontSize="xs" color="#00E5FF" fontWeight="medium">
                      {newUser.governments.join(", ")}
                    </Text>
                  </Box>
                )}
              </Box>
            </FormControl>
          </HStack>
          <Box>
            <Text fontWeight="bold" mb={2} color="#7ecbff">Permissions:</Text>
            <SimpleGrid columns={{ base: 2, md: 3 }} spacing={2}>
              {allPermissions.map(permission => (
                <Checkbox
                  key={permission}
                  isChecked={newUser.permissions?.includes(permission)}
                  onChange={e => handleNewUserPermissionChange(permission, e.target.checked)}
                  color="white"
                  colorScheme="cyan"
                >
                  <Text color="white">{permission}</Text>
                </Checkbox>
              ))}
            </SimpleGrid>
          </Box>
          <Box>
            <Text fontWeight="bold" mb={2} color="#7ecbff">Tab Permissions:</Text>
            <SimpleGrid columns={{ base: 2, md: 3 }} spacing={2}>
              {allTabPermissions.map(tabPermission => (
                <Checkbox
                  key={tabPermission}
                  isChecked={newUser.tabPermissions?.includes(tabPermission)}
                  onChange={e => handleNewUserTabPermissionChange(tabPermission, e.target.checked)}
                  color="white"
                  colorScheme="purple"
                >
                  <Text color="white">{tabPermission.replace('tab_', '').replace('_', ' ')}</Text>
                </Checkbox>
              ))}
            </SimpleGrid>
          </Box>
          <Button
            colorScheme="cyan"
            onClick={handleCreateUser}
            isLoading={loading}
            loadingText="Creating..."
            alignSelf="flex-start"
            bg="#00E5FF"
            color="#101114"
            _hover={{ bg: "#00B8D9" }}
          >
            Create Admin User
          </Button>
        </VStack>
      </Box>
      {/* List Admin Users & Permissions */}
      <Box>
        <Text fontWeight="bold" mb={4} color="#7ecbff">Existing Admin Users</Text>
        {loading ? (
          <Loading />
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            {users.map(user => (
              <Box key={user.username} p={4} borderWidth={1} borderRadius="md" bg="rgba(255,255,255,0.05)" border="1px solid rgba(255,255,255,0.15)">
                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="bold" color="#e0eaff">{user.username}</Text>
                  <Badge colorScheme={user.role === 'main-admin' ? 'purple' : 'cyan'} bg={user.role === 'main-admin' ? 'purple.500' : '#00E5FF'} color={user.role === 'main-admin' ? 'white' : '#101114'}>
                    {user.role === 'main-admin' ? 'MAIN-ADMIN' : 'ADMIN'}
                  </Badge>
                </HStack>
                <Text fontSize="sm" color="gray.400" mb={1}>Governments: {Array.isArray(user.governments) ? user.governments.join(", ") : user.government || "-"}</Text>
                <Text fontSize="sm" color="gray.400" mb={3}>Permissions:</Text>
                <Stack spacing={1}>
                  {allPermissions.map(permission => (
                    <Checkbox
                      key={permission}
                      isChecked={user.permissions?.includes(permission)}
                      onChange={e => handlePermissionChange(user.username, permission, e.target.checked)}
                      isDisabled={
                        loading ||
                        user.role === 'main-admin' ||
                        !currentUser ||
                        currentUser.role !== 'main-admin'
                      }
                      size="sm"
                      color="white"
                      colorScheme="cyan"
                    >
                      <Text color="white">{permission}</Text>
                    </Checkbox>
                  ))}
                </Stack>
                <Text fontSize="sm" color="gray.400" mb={2} mt={3}>Tab Permissions:</Text>
                <Stack spacing={1}>
                  {allTabPermissions.map(tabPermission => (
                    <Checkbox
                      key={tabPermission}
                      isChecked={user.tabPermissions?.includes(tabPermission)}
                      onChange={e => handleTabPermissionChange(user.username, tabPermission, e.target.checked)}
                      isDisabled={
                        loading ||
                        user.role === 'main-admin' ||
                        !currentUser ||
                        currentUser.role !== 'main-admin'
                      }
                      size="sm"
                      color="white"
                      colorScheme="purple"
                    >
                      <Text color="white">{tabPermission.replace('tab_', '').replace('_', ' ')}</Text>
                    </Checkbox>
                  ))}
                </Stack>

                {/* Password Change Section - Only for Main Admin */}
                {currentUser?.role === 'main-admin' && (
                  <Box mt={4} pt={3} borderTop="1px solid rgba(255,255,255,0.15)">
                    <HStack spacing={2}>
                      <Button
                        size="sm"
                        colorScheme="orange"
                        onClick={() => showPasswordChangeForm(user.username)}
                        isDisabled={loading}
                      >
                        Change Password
                      </Button>
                      {user.username !== currentUser?.username && (
                        <Button
                          size="sm"
                          colorScheme="red"
                          onClick={() => showDeleteConfirmation(user.username)}
                          isDisabled={loading}
                        >
                          Delete User
                        </Button>
                      )}
                    </HStack>
                  </Box>
                )}
              </Box>
            ))}
          </SimpleGrid>
        )}
      </Box>

      {/* Password Change Modal */}
      {passwordChange.isVisible && (
        <Box
          position="fixed"
          top="0"
          left="0"
          right="0"
          bottom="0"
          bg="rgba(0,0,0,0.8)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          zIndex="1000"
        >
          <Box
            bg="rgba(255,255,255,0.1)"
            borderRadius="2xl"
            p={6}
            minW="400px"
            border="1px solid rgba(255,255,255,0.2)"
            backdropFilter="blur(10px)"
          >
            <Heading size="md" mb={4} color="#00E5FF">Change Password</Heading>
            <Text color="white" mb={4}>User: {passwordChange.username}</Text>

            <VStack spacing={4}>
              <FormControl>
                <FormLabel color="#7ecbff">New Password</FormLabel>
                <Input
                  type="password"
                  placeholder="Enter new password"
                  value={passwordChange.newPassword}
                  onChange={e => setPasswordChange(prev => ({ ...prev, newPassword: e.target.value }))}
                  bg="rgba(255,255,255,0.1)"
                  color="white"
                  border="1px solid rgba(255,255,255,0.2)"
                  _placeholder={{ color: "gray.400" }}
                  _hover={{ borderColor: "#00E5FF" }}
                  _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
                />
              </FormControl>

              <FormControl>
                <FormLabel color="#7ecbff">Confirm Password</FormLabel>
                <Input
                  type="password"
                  placeholder="Confirm new password"
                  value={passwordChange.confirmPassword}
                  onChange={e => setPasswordChange(prev => ({ ...prev, confirmPassword: e.target.value }))}
                  bg="rgba(255,255,255,0.1)"
                  color="white"
                  border="1px solid rgba(255,255,255,0.2)"
                  _placeholder={{ color: "gray.400" }}
                  _hover={{ borderColor: "#00E5FF" }}
                  _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
                />
              </FormControl>

              <HStack spacing={3} width="100%" justify="flex-end">
                <Button
                  variant="outline"
                  onClick={() => setPasswordChange({ username: '', newPassword: '', confirmPassword: '', isVisible: false })}
                  isDisabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  colorScheme="orange"
                  onClick={handlePasswordChange}
                  isLoading={loading}
                  loadingText="Updating..."
                >
                  Update Password
                </Button>
              </HStack>
            </VStack>
          </Box>
        </Box>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmation.isVisible && (
        <Box
          position="fixed"
          top="0"
          left="0"
          right="0"
          bottom="0"
          bg="rgba(0,0,0,0.8)"
          display="flex"
          alignItems="center"
          justifyContent="center"
          zIndex="1000"
        >
          <Box
            bg="rgba(255,255,255,0.1)"
            borderRadius="2xl"
            p={6}
            minW="400px"
            border="1px solid rgba(255,0,0,0.3)"
            backdropFilter="blur(10px)"
          >
            <Heading size="md" mb={4} color="#FF6B6B">Delete User</Heading>
            <Text color="white" mb={2}>Are you sure you want to delete the user:</Text>
            <Text fontWeight="bold" color="#FF6B6B" mb={4} fontSize="lg">
              {deleteConfirmation.username}
            </Text>
            <Text color="gray.300" mb={6} fontSize="sm">
              This action cannot be undone. The user will be permanently removed from the system.
            </Text>

            <HStack spacing={3} width="100%" justify="flex-end">
              <Button
                variant="outline"
                onClick={() => setDeleteConfirmation({ username: '', isVisible: false })}
                isDisabled={loading}
              >
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleDeleteUser}
                isLoading={loading}
                loadingText="Deleting..."
              >
                Delete User
              </Button>
            </HStack>
          </Box>
        </Box>
      )}
    </Box>
  );
}


// Main Admin Page Component
function AdminPageContent({ activeTab, sidebarSections }) {
  const router = useRouter();
  const { refreshUser, user: authUser, hasPermission, hasTabPermission } = useAuth();
  const config = useRuntimeEnv();

  // Remove unused local loading state; rely on auth loading instead
  const [actionLoading, setActionLoading] = useState({});
  const [logoutLoading, setLogoutLoading] = useState(false);
  const [refreshingPermissions, setRefreshingPermissions] = useState(false);
  const toast = useToast();

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { approvedUsers, pendingUsers } = useUsersData();
  const { fetchDashboardData } = useLiveClients();

  useEffect(() => {
    refreshUser();
  }, []);

  const handleLogout = async () => {
    setLogoutLoading(true);
    try {
      // Clear local storage
      localStorage.removeItem("currentUser");
      localStorage.removeItem("adminToken");

      toast({
        title: "Logged out",
        description: "You have been successfully logged out",
        status: "success",
        duration: 1000,
        isClosable: true,
      });

      // Redirect to login page immediately
      router.push("/admin/login");
    } catch (error) {
      console.error("Logout error:", error);
      toast({
        title: "Error",
        description: "Error during logout",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLogoutLoading(false);
    }
  };

  const handleUserAction = async (username, action) => {
    setActionLoading((prev) => ({ ...prev, [username]: true }));
    try {
      const STATUS_UPDATE = async (status) => {
        const payload = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, status }) };
        try {
          const res = await fetch('/api/multi/client/status/update', payload);
          let data = null; try { data = await res.json(); } catch { }
          const ok = res.ok && (!!(data && ((data.s1 && data.s1.ok) || (data.s2 && data.s2.ok))) || !data);
          if (ok) {
            toast({ title: 'Success!', description: `User ${status} set successfully`, status: 'success', duration: 3000, isClosable: true });
          } else {
            toast({ title: 'Partial failure', description: 'Could not update status on all servers', status: 'warning', duration: 4000, isClosable: true });
          }
        } catch (e) {
          toast({ title: 'Error', description: 'Failed to update user status', status: 'error', duration: 3000, isClosable: true });
        } finally {
          // Proactively refresh dashboard state soon and later
          setTimeout(() => fetchDashboardData?.(), 600);
          setTimeout(() => fetchDashboardData?.(), 2000);
        }
      };

      // Handle Redis-only status changes fast (pause/block/normal)
      if (['pause', 'block', 'normal'].includes(action)) {
        // Fire-and-forget; clear spinner immediately for snappy UI
        STATUS_UPDATE(action);
        return;
      }

      // For reject, mark as blocked in Redis and also perform FS move
      if (action === 'reject') {
        // Do Redis update in background for speed
        STATUS_UPDATE('block');
        // Then do FS update
        const response = await fetch('/api/users/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, action: 'reject' }) });
        const result = await response.json();
        if (!result.success) throw new Error(result.error);
        toast({ title: 'Success!', description: result.message, status: 'success', duration: 3000, isClosable: true });
        return;
      }

      // For approve/pending -> perform FS transition
      if (['approve', 'pending'].includes(action)) {
        const response = await fetch('/api/users/add', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, action })
        });
        const result = await response.json();
        if (!result.success) throw new Error(result.error);
        toast({ title: 'Success!', description: result.message, status: 'success', duration: 3000, isClosable: true });
        return;
      }

      toast({ title: 'Info', description: 'No changes applied', status: 'info', duration: 2000, isClosable: true });
    } catch (error) {
      console.error("Error processing user action:", error);
      toast({
        title: "Error",
        description: "Failed to process user action",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      // Clear spinner quickly regardless of background status call
      setActionLoading((prev) => ({ ...prev, [username]: false }));
    }
  };




  if (authLoading) {
    return <Loading message="Loading admin panel..." minHeight="100vh" />;
  }

  return (
    <Box
      bg="#101114"
      minH="100vh"
      py={8}
      px={{ base: 2, md: 0 }}
      style={{
        backgroundAttachment: 'fixed',
        minHeight: '100vh',
        width: '100%',
      }}
    >
      {/* Header */}
      <Box textAlign="center" mb={10}>
        <Heading
          as="h1"
          size="2xl"
          color="#e0eaff"
          fontWeight="extrabold"
          letterSpacing="wide"
          textShadow="0 4px 24px #000a, 0 1px 0 #1a365d"
        >
          Mirando Solutions
        </Heading>
        <Text color="#7ecbff" fontSize="xl" mt={2} fontWeight="semibold" letterSpacing="wider">
          Admin Panel
        </Text>
      </Box>

      <Box maxW="7xl" mx="auto" px={{ base: 0, md: 4 }}>
        {/* Main Content by Sidebar Selection - with permission checks */}
        {(() => {
          // Check if user has tab permission for the active tab
          const activeTabConfig = sidebarSections.find(tab => tab.label === activeTab);
          const hasTabAccess = !activeTabConfig?.tabPermission || hasTabPermission(activeTabConfig.tabPermission);

          if (!hasTabAccess) {
            return (
              <Box color="white" textAlign="center" py={10}>
                <Text fontSize="2xl" fontWeight="bold" color="red.300">Access Denied</Text>
                <Text color="gray.400">You don't have permission to access this tab.</Text>
              </Box>
            );
          }

          switch (activeTab) {
            case "Dashboard":
              return (
                <Dashboard />
              );
            case "Available Users":
              return (
                <ApprovedUsersSection
                  approvedUsers={approvedUsers}
                  actionLoading={actionLoading}
                  setActionLoading={setActionLoading}
                />
              );
            case "Users":
              return (
                <Users
                  onUserAction={handleUserAction}
                  actionLoading={actionLoading}
                />
              );
            case "Settings":
              return (
                <Box color="white" py={10}>
                  <Text fontSize="2xl" fontWeight="bold" mb={8}>Settings</Text>

                  {/* Tab Permissions Info */}

                  <Permission permission={"edit_user_permissions"}>
                    <Box
                      bg="rgba(255,255,255,0.10)"
                      borderRadius="2xl"
                      boxShadow="0 8px 32px 0 rgba(31, 38, 135, 0.37)"
                      border="1px solid rgba(255,255,255,0.18)"
                      backdropFilter="blur(8px)"
                      mb={10}
                      p={{ base: 2, md: 0 }}
                    >
                      <AdminUsersManager />
                    </Box>
                  </Permission>
                  <Button
                    colorScheme="red"
                    size="lg"
                    mt={4}
                    isLoading={logoutLoading}
                    loadingText="Logging out..."
                    onClick={handleLogout}
                  >
                    Logout
                  </Button>
                </Box>
              );
            default:
              return (
                <Box color="white" textAlign="center" py={10}>
                  <Text fontSize="2xl" fontWeight="bold">Page Not Found</Text>
                  <Text color="gray.400">The requested page could not be found.</Text>
                </Box>
              );
          }
        })()}
      </Box>
    </Box>
  );
}

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  if (isLoading) return <Loading />;
  if (!isAuthenticated || !user?.username) {
    if (typeof window !== "undefined") window.location.href = "/admin/login";
    return null;
  }
  return <>{children}</>;
}

// Main Export
export default function AdminPage() {
  const { hasPermission, hasTabPermission } = useAuth();

  // Sidebar items with tab permission requirements
  const sidebarSections = [
    { label: "Dashboard", icon: <FiGrid size={24} color="#00E5FF" />, tabPermission: "tab_dashboard" },
    { label: "Available Users", icon: <FiUserCheck size={24} color="#00E5FF" />, tabPermission: "tab_available_users" },
    { label: "Users", icon: <FiUsers size={24} color="#00E5FF" />, tabPermission: "tab_users" },
    { label: "Actions", icon: <FiActivity size={24} color="#00E5FF" />, href: "/admin/actions", tabPermission: "tab_actions" },
    { label: "Settings", icon: <FiSettings size={24} color="#00E5FF" />, tabPermission: "tab_settings" },
    { label: "Take Photo", icon: <FiCamera size={24} color="#00E5FF" />, href: "/result-photo", tabPermission: "tab_take_photo" },
  ];

  // Filter tabs based on user tab permissions
  const allowedTabs = sidebarSections.filter(item =>
    !item.tabPermission || hasTabPermission(item.tabPermission)
  );

  // Initialize activeTab with the first allowed tab or fallback to "Dashboard"
  const [activeTab, setActiveTab] = React.useState(() => {
    return allowedTabs.length > 0 ? allowedTabs[0].label : "Dashboard";
  });

  // Ensure the active tab is allowed, otherwise default to first allowed tab
  React.useEffect(() => {
    const activeTabAllowed = allowedTabs.some(tab => tab.label === activeTab);
    if (!activeTabAllowed && allowedTabs.length > 0) {
      setActiveTab(allowedTabs[0].label);
    }
  }, [allowedTabs, activeTab]);
  // Collapsed state: show only icons on base (mobile), icons+labels on md+
  return (
    <ProtectedRoute requireAdmin={true}>
      <Flex minH="100vh" bg="#101114">
        {/* Sidebar */}
        <Box
          as="nav"
          w={{ base: "64px", md: "220px" }}
          bg="#181A20"
          color="#00E5FF"
          py={8}
          px={2}
          display="flex"
          flexDirection="column"
          alignItems="center"
          boxShadow="2xl"
          position="fixed"
          left={0}
          top={0}
          bottom={0}
          zIndex={100}
        >
          {/* Brand Logo */}
          <Box mb={6}>
            <Image
              src="/112.png"
              alt="Mirando Solutions Logo"
              boxSize={{ base: "100px", md: "120px" }}
              objectFit="contain"
              mx="auto"
              mb={2}
            />
          </Box>
          {/* Menu Heading */}
          <Box mb={10}>
            <Heading size="md" color="#00E5FF" letterSpacing="wider">Menu</Heading>
          </Box>
          {/* Nav Items, with section spacing - only show tabs user has permission for */}
          <VStack spacing={2} align="stretch">
            {allowedTabs.map(item => (
              <SidebarNavItem
                key={item.label}
                icon={item.icon}
                label={item.label}
                active={activeTab === item.label}
                onClick={() => {
                  if (item.href) {
                    window.location.href = item.href;
                  } else {
                    setActiveTab(item.label);
                  }
                }}
              />
            ))}
          </VStack>
        </Box>
        {/* Main Content */}
        <Box
          flex={1}
          ml={{ base: "64px", md: "220px" }}
          minH="100vh"
          bg="#101114"
          p={{ base: 2, md: 8 }}
        >
          <AdminPageContent activeTab={activeTab} sidebarSections={sidebarSections} />
        </Box>
      </Flex>
    </ProtectedRoute>
  );
}

// SidebarNavItem component for sidebar navigation
import { useBreakpointValue } from "@chakra-ui/react";
import Dashboard from "../components/Dashboard";
import Users from "../components/Users";
import ClientCard, { ApprovedUserCard, ApprovedUsersSection } from "../components/ClientCard";


function SidebarNavItem({ icon, label, active, onClick }) {
  // Show label only on md+ screens
  const showLabel = useBreakpointValue({ base: false, md: true });
  return (
    <Button
      variant={active ? "solid" : "ghost"}
      color={active ? "#101114" : "#00E5FF"}
      bg={active ? "#00E5FF" : "transparent"}
      fontWeight="bold"
      fontSize="md"
      w="full"
      justifyContent={showLabel ? "flex-start" : "center"}
      borderRadius="lg"
      _hover={{ bg: active ? "#00B8D9" : "#181A20", color: "#00E5FF" }}
      mb={0.5}
      px={showLabel ? 4 : 0}
      py={3}
      h="44px"
      transition="all 0.2s"
      boxShadow={active ? "md" : undefined}
      onClick={onClick}
    >
      <Box as="span" mr={showLabel ? 3 : 0} display="flex" alignItems="center" justifyContent="center">{icon}</Box>
      {showLabel && <Text fontWeight="bold">{label}</Text>}
    </Button>
  );
}
