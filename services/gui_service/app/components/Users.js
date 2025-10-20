import React, { useContext, useState, useEffect, useMemo, useCallback } from "react";
import {
  Box,
  Input,
  Button,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Table,
  Thead,
  Tr,
  Th,
  Tbody,
  Td,
  Badge,
  Text,
  Flex,
  Image,
  HStack,
  VStack,
  Spinner,
  Center,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  IconButton,
  Tooltip,
} from "@chakra-ui/react";
import { ViewIcon } from "@chakra-ui/icons";
import { useUserLookup, useUsersData, useLiveClients } from "../DashboardContext";
import { useRuntimeEnv } from "../contexts/RuntimeEnvContext";
import Permission from "./Permission";
import { EnhancedSearchComponent, usePaginatedData } from "./UsersComponents";

// Helper for badge color
function statusColor(status) {
  switch (status) {
    case "Pending":
      return "yellow";
    case "Approved":
      return "green";
    case "Blocked":
    case "Rejected":
      return "red";
    default:
      return "blue";
  }
}

// Memoized table row so only this row re-renders on approve/reject
const UserRow = React.memo(function UserRow({
  username,
  name,
  nationalId,
  government,
  department,
  tabLabel,
  showActions,
  onOpenDetails,
  onUserAction,
  onAfterAction,
}) {
  const [loading, setLoading] = useState({ approve: false, reject: false });
  const isBusy = loading.approve || loading.reject;

  const handleAction = async (action) => {
    setLoading(prev => ({ ...prev, [action]: true }));
    try {
      await onUserAction?.(username, action);
      onAfterAction?.(action);
    } finally {
      setLoading(prev => ({ ...prev, [action]: false }));
    }
  };

  return (
    <Tr _hover={{ bg: "rgba(255,255,255,0.02)" }}>
      <Td color="#e0eaff" borderColor="rgba(255,255,255,0.1)">{username}</Td>
      <Td color="#e0eaff" borderColor="rgba(255,255,255,0.1)">{name}</Td>
      <Td color="#e0eaff" borderColor="rgba(255,255,255,0.1)">{nationalId}</Td>
      <Td borderColor="rgba(255,255,255,0.1)">
        <Badge colorScheme={statusColor(tabLabel)} variant="solid">
          {tabLabel}
        </Badge>
      </Td>
      <Td color="#e0eaff" borderColor="rgba(255,255,255,0.1)">{government}</Td>
      <Td color="#e0eaff" borderColor="rgba(255,255,255,0.1)">{department}</Td>
      <Td borderColor="rgba(255,255,255,0.1)">
        <HStack spacing={2}>
          <Tooltip label="View Details">
            <IconButton
              icon={<ViewIcon />}
              size="xs"
              variant="outline"
              colorScheme="blue"
              onClick={onOpenDetails}
            />
          </Tooltip>

          {showActions && (
            <>
              <Permission permission="approve_user">
                <Button
                  size="xs"
                  colorScheme="green"
                  onClick={() => handleAction("approve")}
                  isLoading={loading.approve}
                  isDisabled={isBusy}
                  loadingText="Approving..."
                >
                  Approve
                </Button>
              </Permission>
              <Permission permission="reject_user">
                <Button
                  size="xs"
                  colorScheme="red"
                  onClick={() => handleAction("reject")}
                  isLoading={loading.reject}
                  isDisabled={isBusy}
                  loadingText="Rejecting..."
                >
                  Reject
                </Button>
              </Permission>
            </>
          )}
        </HStack>
      </Td>
    </Tr>
  );
});

// User Details Modal Component
const UserDetailsModal = ({ user, isOpen, onClose, onAction, actionLoading }) => {
  const { findUserByNationalId, findUserByUsername } = useUserLookup();
  const config = useRuntimeEnv();

  // Get full user details from Excel data
  let fullUserData = null;
  if (user?.nationalId) {
    fullUserData = findUserByNationalId(user.nationalId);
  }
  if (!fullUserData && user?.username) {
    fullUserData = findUserByUsername(user.username);
  }

  const displayUser = { ...user, ...fullUserData };

  // Local modal loading state so only the clicked button shows spinner
  const [modalLoading, setModalLoading] = useState({ approve: false, reject: false });
  const modalBusy = modalLoading.approve || modalLoading.reject;

  // Get user photo URL
  const getUserPhotoUrl = (user) => {
    if (!user || !user.username) return null;

    let folder = "pending";
    let base = config?.guiData || "/app/gui_data";

    if (user.status === 'approved') {
      folder = "";
      base = config?.userDatabase || "";
    } else if (user.status === 'blocked' || user.status === 'rejected') {
      folder = "rejected";
      base = config?.guiData || "";
    }

    return `/api/user-photo?username=${encodeURIComponent(user.username)}&path=${folder}&base=${encodeURIComponent(base)}`;
  };

  const imageUrl = getUserPhotoUrl(displayUser);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent bg="rgba(255,255,255,0.05)" border="1px solid rgba(255,255,255,0.15)">
        <ModalHeader color="#00E5FF">User Details</ModalHeader>
        <ModalCloseButton color="#00E5FF" />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Flex direction={{ base: "column", md: "row" }} gap={4}>
              <Image
                borderRadius="lg"
                boxSize="200px"
                src={imageUrl}
                alt={`${displayUser.name || displayUser.username} photo`}
                objectFit="cover"
                fallback={
                  <Box
                    bg="gray.200"
                    borderRadius="lg"
                    boxSize="200px"
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <Text>No Image</Text>
                  </Box>
                }
              />
              <VStack align="start" spacing={3} flex={1}>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">Username</Text>
                  <Text fontSize="lg" color="#e0eaff">{displayUser.username || 'N/A'}</Text>
                </Box>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">Name</Text>
                  <Text fontSize="lg" color="#e0eaff">{displayUser.name || 'N/A'}</Text>
                </Box>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">National ID</Text>
                  <Text fontSize="lg" color="#e0eaff">{displayUser.nationalId || displayUser.national_id || displayUser.nationalID || displayUser.nId || 'N/A'}</Text>
                </Box>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">Department</Text>
                  <Text fontSize="lg" color="#e0eaff">{displayUser.department || 'N/A'}</Text>
                </Box>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">Government</Text>
                  <Text fontSize="lg" color="#e0eaff">{displayUser.government || 'N/A'}</Text>
                </Box>
                <Box>
                  <Text fontWeight="bold" fontSize="sm" color="gray.400">Status</Text>
                  <Badge
                    colorScheme={statusColor(displayUser.status)}
                    variant="solid"
                  >
                    {displayUser.status?.toUpperCase() || 'UNKNOWN'}
                  </Badge>
                </Box>
              </VStack>
            </Flex>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <HStack spacing={3}>
            {displayUser.status === 'Pending' && (
              <>
                <Permission permission="approve_user">
                  <Button
                    colorScheme="green"
                    onClick={async () => {
                      setModalLoading(prev => ({ ...prev, approve: true }));
                      try {
                        await onAction(displayUser.username, 'approve');
                      } finally {
                        setModalLoading(prev => ({ ...prev, approve: false }));
                      }
                    }}
                    isLoading={modalLoading.approve}
                    isDisabled={modalBusy}
                    size="sm"
                  >
                    Approve
                  </Button>
                </Permission>
                <Permission permission="reject_user">
                  <Button
                    colorScheme="red"
                    onClick={async () => {
                      setModalLoading(prev => ({ ...prev, reject: true }));
                      try {
                        await onAction(displayUser.username, 'reject');
                      } finally {
                        setModalLoading(prev => ({ ...prev, reject: false }));
                      }
                    }}
                    isLoading={modalLoading.reject}
                    isDisabled={modalBusy}
                    size="sm"
                  >
                    Reject
                  </Button>
                </Permission>
              </>
            )}
            <Button variant="ghost" onClick={onClose} color="#00E5FF">Close</Button>
          </HStack>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Enhanced UserTable component with pagination
function UserTable({ users, showActions, onUserAction, actionLoading, tabLabel, status }) {
  const [selectedUser, setSelectedUser] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { findUserByNationalId, findUserByUsername } = useUserLookup();

  // Maintain a local users list so we can optimistically update UI without re-rendering the whole list
  const [localUsers, setLocalUsers] = useState(users);
  useEffect(() => { setLocalUsers(users); }, [users]);

  // Use pagination hook
  const {
    currentData,
    currentPage,
    pageSize,
    totalItems,
    isSearching,
    handlePageChange,
    handleSearchResults
  } = usePaginatedData(localUsers, 50);

  // Helper to get the national ID field from a user object
  function getNationalId(user) {
    if (!user) return "-";
    return user.national_id || user.nationalID || user.nationalid || user.nId || "-";
  }

  // Open user details modal
  const openUserDetails = (user) => {
    let userWithExcelData = null;

    if (user.nationalId) {
      userWithExcelData = findUserByNationalId(user.nationalId);
    }

    if (!userWithExcelData && user.username) {
      userWithExcelData = findUserByUsername(user.username);
    }

    setSelectedUser({
      ...user,
      ...userWithExcelData,
      status: tabLabel
    });
    onOpen();
  };

  return (
    <Box>
      {/* Search Component */}
      <EnhancedSearchComponent
        onSearchResults={handleSearchResults}
        status={status}
        placeholder={`Search ${tabLabel.toLowerCase()} users by username, ID, or name...`}
        searchEndpoint="/api/users/read"
      />

      {/* Results Summary */}
      <Flex justify="space-between" align="center" mb={4}>
        <Text fontSize="sm" color="gray.400">
          {isSearching
            ? `Showing search results`
            : `Showing ${(currentPage - 1) * pageSize + 1}-${Math.min(currentPage * pageSize, totalItems)} of ${totalItems} users`
          }
        </Text>
        <Badge colorScheme="blue" variant="outline">
          Page {currentPage} of {Math.ceil(totalItems / pageSize) || 1}
        </Badge>
      </Flex>

      {/* Table */}
      <Box overflowX="auto" bg="rgba(255,255,255,0.02)" borderRadius="md" border="1px solid rgba(255,255,255,0.1)">
        <Table variant="simple" size="sm">
          <Thead bg="rgba(255,255,255,0.05)">
            <Tr>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Username</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Name</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">National ID</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Status</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Government</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Department</Th>
              <Th color="#00E5FF" borderColor="rgba(255,255,255,0.1)">Actions</Th>
            </Tr>
          </Thead>
          <Tbody>
            {currentData.length === 0 ? (
              <Tr>
                <Td colSpan={7} color="gray.400" textAlign="center" py={8}>
                  {isSearching ? 'No users found matching your search' : `No ${tabLabel.toLowerCase()} users found`}
                </Td>
              </Tr>
            ) : (
              currentData.map((user, index) => (
                <UserRow
                  key={user.username || index}
                  username={user.username}
                  name={user.name || "-"}
                  nationalId={getNationalId(user)}
                  government={user.government || "-"}
                  department={user.department || "-"}
                  tabLabel={tabLabel}
                  showActions={showActions}
                  onOpenDetails={() => openUserDetails(user)}
                  onUserAction={async (u, action) => {
                    // Keep onUserAction signature backward compatible
                    await onUserAction?.(u, action);
                  }}
                  onAfterAction={(action) => {
                    if (action === 'approve' || action === 'reject') {
                      // Optimistically remove the user from local list so only this row disappears
                      setLocalUsers(prev => prev.filter(x => x.username !== user.username));
                    }
                  }}
                />
              ))
            )}
          </Tbody>
        </Table>
      </Box>

      {/* Pagination */}
      {totalItems > pageSize && (
        <PaginationComponent
          currentPage={currentPage}
          totalItems={totalItems}
          itemsPerPage={pageSize}
          onPageChange={handlePageChange}
          maxVisiblePages={7}
        />
      )}

      {/* Summary */}
      <Box mt={4} p={3} bg="rgba(0,229,255,0.1)" borderRadius="md" border="1px solid rgba(0,229,255,0.3)">
        <Text fontSize="sm" color="#00E5FF" fontWeight="bold">
          Total {tabLabel} Users: {localUsers.length}
        </Text>
      </Box>

      {/* User Details Modal */}
      {selectedUser && (
        <UserDetailsModal
          user={selectedUser}
          isOpen={isOpen}
          onClose={onClose}
          onAction={async (username, action) => {
            await onUserAction?.(username, action);
            if (action === 'approve' || action === 'reject') {
              setLocalUsers(prev => prev.filter(x => x.username !== username));
              onClose();
            }
          }}
          actionLoading={actionLoading}
        />
      )}
    </Box>
  );
}

// Updated main Users component
export default function Users({
  onUserAction,
  actionLoading = {},
}) {


  const config = useRuntimeEnv();

  const [activeTab, setActiveTab] = useState(0);
  const { pendingUsers, rejectedUsers, approvedUsers } = useUsersData();


  // Handle user selection from search
  const handleUserSelect = (user) => {
    setSelectedUser(user);
  };

  // Memoize tab data to prevent unnecessary recalculations
  const tabData = useMemo(() => [
    {
      label: "Pending",
      users: pendingUsers,
      showActions: true,
      status: "pending",
      color: "yellow"
    },
    {
      label: "Rejected",
      users: rejectedUsers,
      showActions: false,
      status: "blocked",
      color: "red"
    },
  ], [pendingUsers, rejectedUsers]);

  // Helper to determine status for a user
  function getUserStatus(user) {
    if (blocked.some(u => u.username === user.username)) return "Rejected";
    if (approved.some(u => u.username === user.username)) return "Approved";
    if (pending.some(u => u.username === user.username)) return "Pending";
    return "Unknown";
  }

  // Helper to get the national ID field from a user object
  function getNationalId(user) {
    if (!user) return "-";
    return user.national_id || user.nationalID || user.nationalid || user.nId || "-";
  }

  // Helper to get the user's photo from active clients (if any)
  function getUserPhotoUrl(user) {
    if (!user || !user.username) return null;

    let folder = "pending";
    let base = config?.guiData || "/app/gui_data";
    if (approved.some(u => u.username === user.username)) {
      folder = "";
      base = config?.userDatabase || "";
    }
    if (blocked.some(u => u.username === user.username)) {
      folder = "rejected";
      base = config?.guiData || "";
    }
    return `/api/user-photo?username=${encodeURIComponent(user.username)}&path=${folder}${base ? `&base=${encodeURIComponent(base)}` : ""}`;
  }

  return (
    <Box
      p={6}
      maxW="100%"
      mx="auto"
      bg="rgba(255,255,255,0.02)"
      borderRadius="xl"
      border="1px solid rgba(255,255,255,0.1)"
    >
      {/* Header */}
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Text fontSize="2xl" fontWeight="bold" color="#00E5FF" mb={2}>
            User Management
          </Text>
          <Text fontSize="md" color="gray.400">
            Manage pending and rejected users
          </Text>
        </Box>


        {/* Tabs for different user categories */}
        <Tabs
          variant="enclosed"
          colorScheme="cyan"
          isFitted
          index={activeTab}
          onChange={setActiveTab}
          bg="rgba(255,255,255,0.02)"
          borderRadius="lg"
          border="1px solid rgba(255,255,255,0.1)"
        >
          <TabList bg="rgba(255,255,255,0.05)" borderTopRadius="lg">
            {tabData.map((tab, index) => (
              <Tab
                key={tab.label}
                color={activeTab === index ? "#101114" : "#00E5FF"}
                bg={activeTab === index ? "#00E5FF" : "transparent"}
                _hover={{ bg: activeTab === index ? "#00B8D9" : "rgba(0,229,255,0.1)" }}
                _selected={{ bg: "#00E5FF", color: "#101114" }}
                fontWeight="bold"
                border="none"
              >
                {tab.label} ({tab.users.length})
              </Tab>
            ))}
          </TabList>

          <TabPanels>
            {tabData.map((tab, index) => (
              <TabPanel key={tab.label} p={6}>
                <UserTable
                  users={tab.users}
                  showActions={tab.showActions}
                  onUserAction={onUserAction}
                  actionLoading={actionLoading}
                  tabLabel={tab.label}
                  status={tab.status}
                />
              </TabPanel>
            ))}
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}