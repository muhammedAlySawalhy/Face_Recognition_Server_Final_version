import React, { useState, useMemo, useCallback } from "react";
import {
    Box,
    Button,
    Text,
    HStack,
    VStack,
    Flex,
    SimpleGrid,
    Heading,
    IconButton,
    Tooltip,
    useDisclosure,
    useToast,
    Center,
    Badge,
} from "@chakra-ui/react";
import { ViewIcon } from "@chakra-ui/icons";
import { useUserLookup, useLiveClients } from "../DashboardContext";
import { useRuntimeEnv } from "../contexts/RuntimeEnvContext";
import Permission from "./Permission";
import {
    PaginationComponent,
    EnhancedSearchComponent,
    usePaginatedData,
} from "./UsersComponents";
import UserDetailsModal from "./UserDetailsModal"; // moved modal to separate file
import dispatchUserAction from "../../lib/utils/dispatchUserAction";

// Card component
function ApprovedUserCard({ user, onAction, getUserStatus }) {
    const status = getUserStatus(user.username);
    const [loading, setLoading] = useState({ pause: false, block: false });

    const handleAction = async (actionType) => {
        setLoading(prev => ({ ...prev, [actionType]: true }));
        try {
            await onAction(user.username, actionType);
        } finally {
            setLoading(prev => ({ ...prev, [actionType]: false }));
        }
    };

    return (
        <Box
            maxW="sm"
            bg="rgba(255,255,255,0.05)"
            border="1px solid rgba(255,255,255,0.15)"
            borderRadius="lg"
            p={4}
            _hover={{
                transform: "translateY(-2px)",
                boxShadow: "lg",
                border: "1px solid rgba(0,229,255,0.3)",
            }}
            transition="all 0.2s"
        >
            <VStack spacing={4}>
                <VStack spacing={2} textAlign="center">
                    <Text fontWeight="bold" fontSize="md" color="#e0eaff" noOfLines={1}>
                        {user.name || user.username}
                    </Text>
                    {user.username && user.name && (
                        <Text fontSize="sm" color="gray.400" noOfLines={1}>
                            @{user.username}
                        </Text>
                    )}
                    <Badge
                        colorScheme={
                            status === "approved"
                                ? "green"
                                : status === "blocked"
                                    ? "red"
                                    : "yellow"
                        }
                        variant="solid"
                    >
                        {status === "approved" ? "NORMAL" : status.toUpperCase()}
                    </Badge>
                    {user.department && (
                        <Text fontSize="xs" color="gray.500" noOfLines={1}>
                            {user.department}
                        </Text>
                    )}
                    {user.government && (
                        <Text fontSize="xs" color="gray.500" noOfLines={1}>
                            {user.government}
                        </Text>
                    )}
                </VStack>

                <HStack spacing={2} width="100%">
                    <Tooltip label="View Details">
                        <IconButton
                            icon={<ViewIcon />}
                            size="sm"
                            variant="outline"
                            colorScheme="blue"
                            onClick={user.onOpenDetails}
                            flex={1}
                        />
                    </Tooltip>

                    <Permission permission="pause_user">
                        <Button
                            size="sm"
                            colorScheme={status === "paused" ? "green" : "yellow"}
                            onClick={() =>
                                handleAction(status === "paused" ? "normal" : "pause")
                            }
                            isLoading={loading.pause}
                            isDisabled={loading.pause || loading.block}
                            flex={1}
                        >
                            {status === "paused" ? "Unpause" : "Pause"}
                        </Button>
                    </Permission>

                    <Permission permission="block_user">
                        <Button
                            size="sm"
                            colorScheme={status === "blocked" ? "green" : "red"}
                            onClick={() =>
                                handleAction(status === "blocked" ? "normal" : "block")
                            }
                            isLoading={loading.block}
                            isDisabled={loading.pause || loading.block}
                            flex={1}
                        >
                            {status === "blocked" ? "Unblock" : "Block"}
                        </Button>
                    </Permission>
                </HStack>
            </VStack>
        </Box>
    );
}

export const ApprovedUsersSection = ({
    approvedUsers,
}) => {
    const { findUserByNationalId, findUserByUsername } = useUserLookup();
    const { isOpen, onOpen, onClose } = useDisclosure();
    const config = useRuntimeEnv();
    const toast = useToast();
    const [selectedUser, setSelectedUser] = useState(null);
    const { pause: pausedList, blocked: blockedList } = useLiveClients();

    // Local state to track optimistic updates
    const [localPausedUsers, setLocalPausedUsers] = useState(new Set());
    const [localBlockedUsers, setLocalBlockedUsers] = useState(new Set());

    // Prepare approved users
    const preparedApprovedUsers = useMemo(() => {
        return approvedUsers.map((user) => {
            let excelData = null;
            if (user.nationalId) {
                excelData = findUserByNationalId(user.nationalId);
            } else if (user.username) {
                excelData = findUserByUsername(user.username);
            }
            return { ...user, ...excelData };
        });
    }, [approvedUsers, findUserByNationalId, findUserByUsername]);

    const { currentData, currentPage, pageSize, totalItems, isSearching, handlePageChange, handleSearchResults } =
        usePaginatedData(preparedApprovedUsers, 50);

    const updateUserStatus = useCallback((username, newStatus) => {
        // Update local state for immediate UI feedback
        setLocalPausedUsers(prev => {
            const next = new Set(prev);
            next.delete(username);
            return next;
        });
        setLocalBlockedUsers(prev => {
            const next = new Set(prev);
            next.delete(username);
            return next;
        });

        if (newStatus === "paused") {
            setLocalPausedUsers(prev => new Set([...prev, username]));
        } else if (newStatus === "blocked") {
            setLocalBlockedUsers(prev => new Set([...prev, username]));
        }
    }, []);

    const getUserStatus = useCallback((username) => {
        // Check local state first for immediate feedback
        if (localBlockedUsers.has(username)) return "blocked";
        if (localPausedUsers.has(username)) return "paused";

        // Fall back to global state
        if (blockedList.some(u => u.username === username)) return "blocked";
        if (pausedList.some(u => u.username === username)) return "paused";

        return "approved";
    }, [blockedList, pausedList, localBlockedUsers, localPausedUsers]);

    const handleUserAction = useCallback(
        async (username, action) => {
            const currentStatus = getUserStatus(username);

            // Optimistic update
            const newStatus =
                action === "pause"
                    ? "paused"
                    : action === "block"
                        ? "blocked"
                        : "approved";
            updateUserStatus(username, newStatus);

            try {
                const STATUS_ENDPOINTS = [
                    config?.endpoints?.s1Update,
                    config?.endpoints?.s2Update,
                ].filter(Boolean);

                await dispatchUserAction({
                    username,
                    action,
                    toast,
                    STATUS_ENDPOINTS,
                });
            } catch (error) {
                // Rollback on error
                updateUserStatus(username, currentStatus);
                toast({
                    title: "Error",
                    description: "Failed to update status",
                    status: "error",
                });
            }
        },
        [config, toast, getUserStatus, updateUserStatus]
    );

    const openUserDetails = (user) => {
        setSelectedUser(user);
        onOpen();
    };

    return (
        <Box>
            <Heading size="md" color="#00E5FF" mb={6}>
                Available Users (Approved)
            </Heading>

            <EnhancedSearchComponent
                onSearchResults={handleSearchResults}
                status="approved"
                placeholder="Search approved users..."
                searchEndpoint="/api/users/read"
            />

            <Flex justify="space-between" align="center" mb={4}>
                <Text fontSize="sm" color="gray.400">
                    {isSearching
                        ? `Showing search results`
                        : `Showing ${(currentPage - 1) * pageSize + 1}-${Math.min(
                            currentPage * pageSize,
                            totalItems
                        )} of ${totalItems} users`}
                </Text>
                <Badge colorScheme="blue" variant="outline">
                    Page {currentPage} of {Math.ceil(totalItems / pageSize)}
                </Badge>
            </Flex>

            {currentData.length > 0 ? (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4} mb={6}>
                    {currentData.map((user) => (
                        <ApprovedUserCard
                            key={user.username}
                            user={{ ...user, onOpenDetails: () => openUserDetails(user) }}
                            onAction={handleUserAction}
                            getUserStatus={getUserStatus}
                        />
                    ))}
                </SimpleGrid>
            ) : (
                <Center py={10}>
                    <VStack>
                        <Text fontSize="lg" color="gray.400">
                            {isSearching
                                ? "No users found matching your search"
                                : "No approved users found"}
                        </Text>
                        <Text fontSize="sm" color="gray.500">
                            {isSearching
                                ? "Try adjusting your search terms"
                                : "Users will appear here once they are approved"}
                        </Text>
                    </VStack>
                </Center>
            )}

            {!isSearching && totalItems > 0 && (
                <PaginationComponent
                    currentPage={currentPage}
                    totalItems={totalItems}
                    itemsPerPage={pageSize}
                    onPageChange={handlePageChange}
                    maxVisiblePages={7}
                />
            )}

            {selectedUser && (
                <UserDetailsModal
                    user={selectedUser}
                    isOpen={isOpen}
                    onClose={onClose}
                    onAction={handleUserAction}
                />
            )}
        </Box>
    );
};
