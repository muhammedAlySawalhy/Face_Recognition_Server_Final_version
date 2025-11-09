import React, { useMemo, useState, useEffect } from 'react';
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalCloseButton,
    ModalBody,
    ModalFooter,
    Button,
    VStack,
    Box,
    Text,
    Image,
    Badge,
    useToast,
    Spinner,
} from '@chakra-ui/react';
import { useRuntimeEnv } from '../contexts/RuntimeEnvContext';
import { useLiveClients } from '../DashboardContext';
import dispatchUserAction from '../../lib/utils/dispatchUserAction';

/**
 * UserDetailsModal
 *
 * Props:
 *  - user: object (must include username; other fields optional)
 *  - isOpen: boolean
 *  - onClose: fn
 *  - onAction: async fn (username, action, opts)  // optional: parent handler (recommended)
 *  - actionLoading: record username->bool (optional) — used to show loading state passed from parent
 *
 * Behavior:
 *  - If `onAction` prop is provided, modal calls onAction(username, action, { STATUS_ENDPOINTS })
 *    expecting the parent to perform optimistic updates and call dispatchUserAction.
 *  - If `onAction` is NOT provided, the modal will call dispatchUserAction(...) directly.
 */
export default function UserDetailsModal({ user = null, isOpen, onClose, onAction, actionLoading = {} }) {
    const toast = useToast();
    const config = useRuntimeEnv?.() || {};
    const [localLoading, setLocalLoading] = useState(false);
    const [photoUrl, setPhotoUrl] = useState(null);
    const [photoLoading, setPhotoLoading] = useState(false);
    const [photoError, setPhotoError] = useState(false);

    // derive status from live clients (if available) for better accuracy
    const { pause: pausedList = [], blocked: blockedList = [] } = useLiveClients?.() || {};

    const currentStatus = useMemo(() => {
        if (!user) return 'approved';
        if (Array.isArray(blockedList) && blockedList.some((u) => u.username === user.username)) return 'blocked';
        if (Array.isArray(pausedList) && pausedList.some((u) => u.username === user.username)) return 'paused';
        return user.status || 'approved';
    }, [user, pausedList, blockedList]);

    const STATUS_ENDPOINTS = useMemo(() => {
        return [config?.endpoints?.s1Update, config?.endpoints?.s2Update].filter(Boolean);
    }, [config?.endpoints?.s1Update, config?.endpoints?.s2Update]);

    // Fetch user photo when user changes
    useEffect(() => {
        if (!user?.username) {
            setPhotoUrl(null);
            setPhotoError(false);
            return;
        }

        const fetchUserPhoto = async () => {
            setPhotoLoading(true);
            setPhotoError(false);
            setPhotoUrl(null);

            try {
                // Try different paths based on user status
                const pathsToTry = [
                    '', // approved users
                    'approved',
                    'pending',
                    'blocked'
                ];

                let photoFound = false;
                for (const path of pathsToTry) {
                    try {
                        const params = new URLSearchParams({
                            username: user.username,
                            path: path
                        });

                        const response = await fetch(`/api/user-photo?${params}`);
                        if (response.ok) {
                            const blob = await response.blob();
                            const url = URL.createObjectURL(blob);
                            setPhotoUrl(url);
                            photoFound = true;
                            break;
                        }
                    } catch (err) {
                        // Continue to next path
                        console.log(`Failed to fetch photo from path "${path}":`, err);
                    }
                }

                if (!photoFound) {
                    setPhotoError(true);
                }
            } catch (error) {
                console.error('Error fetching user photo:', error);
                setPhotoError(true);
            } finally {
                setPhotoLoading(false);
            }
        };

        fetchUserPhoto();

        // Cleanup function to revoke object URL
        return () => {
            if (photoUrl) {
                URL.revokeObjectURL(photoUrl);
            }
        };
    }, [user?.username]);

    const handleActionClick = async (action) => {
        if (!user || !user.username) return;

        setLocalLoading(true);
        try {
            if (typeof onAction === 'function') {
                // parent handles optimistic update + backend call; pass STATUS_ENDPOINTS so parent can use them
                await Promise.resolve(onAction(user.username, action, { STATUS_ENDPOINTS }));
            } else {
                // fallback: call dispatchUserAction directly (no optimistic client-side update)
                await dispatchUserAction({ username: user.username, action, STATUS_ENDPOINTS });
            }

            toast({
                title: 'Success',
                description: `User ${action} action applied.`,
                status: 'success',
                duration: 2000,
                isClosable: true,
            });
        } catch (err) {
            console.error('UserDetailsModal action error:', err);
            toast({
                title: 'Error',
                description: err?.message || 'Failed to update user status',
                status: 'error',
                duration: 3500,
                isClosable: true,
            });
        } finally {
            setLocalLoading(false);
        }
    };

    if (!user) return null;

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="lg">
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>User Details</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <VStack spacing={4} align="stretch">
                        <Box display="flex" gap={4} alignItems="center">
                            {photoLoading ? (
                                <Box
                                    borderRadius="lg"
                                    boxSize="120px"
                                    display="flex"
                                    alignItems="center"
                                    justifyContent="center"
                                    bg="gray.100"
                                >
                                    <Spinner size="md" />
                                </Box>
                            ) : (
                                <Image
                                    borderRadius="lg"
                                    boxSize="120px"
                                    src={photoUrl}
                                    alt={`${user.name || user.username} photo`}
                                    objectFit="cover"
                                    fallback={
                                        <Box
                                            bg="gray.200"
                                            borderRadius="lg"
                                            boxSize="120px"
                                            display="flex"
                                            alignItems="center"
                                            justifyContent="center"
                                        >
                                            <Text fontSize="sm" color="gray.500">
                                                {photoError ? 'No Photo' : 'Loading...'}
                                            </Text>
                                        </Box>
                                    }
                                />
                            )}
                            <VStack align="start" spacing={1}>
                                <Text fontWeight="bold" fontSize="lg">
                                    {user.name || user.username}
                                </Text>
                                <Text fontSize="sm" color="gray.500">
                                    @{user.username}
                                </Text>
                                <Badge
                                    colorScheme={currentStatus === 'approved' ? 'green' : currentStatus === 'blocked' ? 'red' : 'yellow'}
                                    variant="solid"
                                >
                                    {currentStatus === 'approved' ? 'Normal' : currentStatus.toUpperCase()}
                                </Badge>
                            </VStack>
                        </Box>

                        <Box>
                            <Text fontSize="sm" color="gray.600">National ID</Text>
                            <Text fontSize="md">{user.nationalId || 'N/A'}</Text>
                        </Box>

                        <Box>
                            <Text fontSize="sm" color="gray.600">Department</Text>
                            <Text fontSize="md">{user.department || 'N/A'}</Text>
                        </Box>

                        <Box>
                            <Text fontSize="sm" color="gray.600">Government</Text>
                            <Text fontSize="md">{user.government || 'N/A'}</Text>
                        </Box>
                    </VStack>
                </ModalBody>

                {/* <ModalFooter>
                    <Button
                        colorScheme={currentStatus === 'paused' ? 'green' : 'yellow'}
                        onClick={() => handleActionClick(currentStatus === 'paused' ? 'normal' : 'pause')}
                        isLoading={localLoading || !!actionLoading[user.username]}
                        mr={3}
                        size="sm"
                    >
                        {currentStatus === 'paused' ? 'Unpause' : 'Pause'}
                    </Button>

                    <Button
                        colorScheme={currentStatus === 'blocked' ? 'green' : 'red'}
                        onClick={() => handleActionClick(currentStatus === 'blocked' ? 'normal' : 'block')}
                        isLoading={localLoading || !!actionLoading[user.username]}
                        mr={3}
                        size="sm"
                    >
                        {currentStatus === 'blocked' ? 'Unblock' : 'Block'}
                    </Button>

                    <Button variant="ghost" onClick={onClose} size="sm">Close</Button>
                </ModalFooter> */}
            </ModalContent>
        </Modal>
    );
}
