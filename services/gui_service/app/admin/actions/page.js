"use client";

import React, { useState, useEffect, useRef } from "react";
import {
    Box,
    Flex,
    Heading,
    Spinner,
    Image,
    Text,
    VStack,
    HStack,
    Button,
    ButtonGroup,
    Badge,
} from "@chakra-ui/react";

const USERS_PAGE_SIZE = 5; // Number of users to load per page

// Helper to fetch grouped actions from server
async function fetchGroupedActions(groupBy = "day", page = 0, pageSize = USERS_PAGE_SIZE) {
    const res = await fetch(`/api/actions?groupBy=${groupBy}&page=${page}&pageSize=${pageSize}`);
    if (!res.ok) return { data: [], pagination: null };
    return await res.json();
}

// Helper to format date for display
function formatDateForDisplay(dateString) {
    // Check if dateString is valid
    if (!dateString || typeof dateString !== 'string') {
        return 'Unknown Date';
    }

    try {
        // dateString is in format "DD/MM/YYYY-HH_MM" or just "DD/MM/YYYY"
        const [datePart] = dateString.split('-');
        const [day, month, year] = datePart.split('/');

        // Validate date parts
        if (!day || !month || !year) {
            return 'Invalid Date';
        }

        const date = new Date(year, month - 1, day);

        // Check if date is valid
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }

        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    } catch (error) {
        console.error('Error formatting date:', dateString, error);
        return 'Invalid Date';
    }
}

// Helper to format time for display
function formatTimeForDisplay(dateString) {
    // Check if dateString is valid
    if (!dateString || typeof dateString !== 'string') {
        return '';
    }

    try {
        // dateString is in format "DD/MM/YYYY-HH_MM"
        const [, timePart] = dateString.split('-');
        if (!timePart) return '';
        const [hours, minutes] = timePart.split('_');

        // Validate time parts
        if (!hours || !minutes) return '';

        return `${hours}:${minutes}`;
    } catch (error) {
        console.error('Error formatting time:', dateString, error);
        return '';
    }
}

export default function ActionsPage() {
    const [groupBy, setGroupBy] = useState("user-day"); // Default to user-day grouping
    const [dataGroups, setDataGroups] = useState([]);
    const [currentPage, setCurrentPage] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const [expandedItem, setExpandedItem] = useState(null);
    const [expandedSubItem, setExpandedSubItem] = useState(null);
    const [hasMore, setHasMore] = useState(true);
    const [initialLoading, setInitialLoading] = useState(true);
    const [pagination, setPagination] = useState(null);
    const actionsEndRef = useRef();

    // Load data groups based on current groupBy mode
    const loadData = async (page = 0, append = false) => {
        if (page === 0) setInitialLoading(true);
        else setIsLoading(true);

        try {
            const result = await fetchGroupedActions(groupBy, page, USERS_PAGE_SIZE);

            if (result.data && result.data.length > 0) {
                setDataGroups(prev => append ? [...prev, ...result.data] : result.data);
                setPagination(result.pagination);
                setHasMore(result.pagination?.hasMore || false);
            } else {
                setHasMore(false);
            }
        } catch (error) {
            console.error("Error loading data:", error);
            setHasMore(false);
        } finally {
            setIsLoading(false);
            setInitialLoading(false);
        }
    };

    // Initial load
    useEffect(() => {
        // Reset state when groupBy changes
        setCurrentPage(0);
        setExpandedItem(null);
        setExpandedSubItem(null);
        loadData(0, false);
    }, [groupBy]);

    // Load more data for infinite scroll
    const loadMoreData = () => {
        if (!isLoading && hasMore) {
            const nextPage = currentPage + 1;
            setCurrentPage(nextPage);
            loadData(nextPage, true);
        }
    };

    // Observer for infinite scroll
    useEffect(() => {
        if (!hasMore || isLoading || initialLoading) return;

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && hasMore && !isLoading) {
                console.log("Loading more data...");
                loadMoreData();
            }
        }, { threshold: 0.1 });

        if (actionsEndRef.current) {
            observer.observe(actionsEndRef.current);
        }

        return () => observer.disconnect();
    }, [hasMore, isLoading, initialLoading]);

    if (initialLoading) {
        return (
            <Flex bg="#101114" color="#fff" minH="100vh" direction="column" p={6} justify="center" align="center">
                <Spinner size="xl" color="cyan.300" />
                <Text mt={4} color="cyan.300">Loading all actions...</Text>
            </Flex>
        );
    }

    const renderDayView = () => (
        <VStack spacing={4} align="stretch">
            {dataGroups.map((dayGroup) => (
                <Box key={dayGroup.date} bg="#23272f" borderRadius="md" p={4} boxShadow="lg">
                    <Button
                        variant="link"
                        color="cyan.300"
                        fontWeight="bold"
                        fontSize="lg"
                        onClick={() => setExpandedItem(
                            expandedItem === dayGroup.date ? null : dayGroup.date
                        )}
                        _hover={{ color: "cyan.200" }}
                        leftIcon={<Text>{expandedItem === dayGroup.date ? "▼" : "▶"}</Text>}
                    >
                        {formatDateForDisplay(dayGroup.date)} ({dayGroup.actionCount} actions)
                    </Button>

                    {expandedItem === dayGroup.date && (
                        <VStack align="stretch" spacing={3} mt={4}>
                            {dayGroup.actions
                                .slice()
                                .sort((a, b) => b.date.localeCompare(a.date))
                                .map((action, idx) => (
                                    <HStack key={idx} align="center" bg="#181c24" p={4} borderRadius="md" boxShadow="md">
                                        <Image
                                            src={action.imageUrl}
                                            alt={action.description}
                                            boxSize="80px"
                                            borderRadius="md"
                                            fallbackSrc="/placeholder-image.png"
                                        />
                                        <Box flex={1}>
                                            <HStack>
                                                <Text fontWeight="bold" color="cyan.300">{action.clientName}</Text>
                                                <Text fontSize="sm" color="orange.300" fontWeight="bold">
                                                    {formatTimeForDisplay(action.date)}
                                                </Text>
                                            </HStack>
                                            <Text fontSize="sm" color="gray.300">{action.actionType}</Text>
                                            <Text fontSize="sm" color="white">{action.description}</Text>
                                        </Box>
                                    </HStack>
                                ))}
                        </VStack>
                    )}
                </Box>
            ))}
        </VStack>
    );

    const renderUserDayView = () => (
        <VStack spacing={4} align="stretch">
            {dataGroups.map((userGroup) => (
                <Box key={userGroup.username} bg="#23272f" borderRadius="md" p={4} boxShadow="lg">
                    <Button
                        variant="link"
                        color="cyan.300"
                        fontWeight="bold"
                        fontSize="lg"
                        onClick={() => setExpandedItem(
                            expandedItem === userGroup.username ? null : userGroup.username
                        )}
                        _hover={{ color: "cyan.200" }}
                        leftIcon={<Text>{expandedItem === userGroup.username ? "▼" : "▶"}</Text>}
                    >
                        {userGroup.username}
                        <Badge ml={2} colorScheme="orange" variant="solid">
                            {userGroup.actionCount} actions
                        </Badge>
                        <Badge ml={2} colorScheme="blue" variant="solid">
                            {userGroup.dayCount} days
                        </Badge>
                    </Button>

                    {expandedItem === userGroup.username && (
                        <VStack align="stretch" spacing={3} mt={4} ml={4}>
                            {userGroup.dayGroups.map((dayGroup) => (
                                <Box key={`${userGroup.username}-${dayGroup.date}`} bg="#181c24" borderRadius="md" p={3}>
                                    <Button
                                        variant="link"
                                        color="orange.300"
                                        fontWeight="semibold"
                                        fontSize="md"
                                        onClick={() => {
                                            const subKey = `${userGroup.username}-${dayGroup.date}`;
                                            setExpandedSubItem(expandedSubItem === subKey ? null : subKey);
                                        }}
                                        _hover={{ color: "orange.200" }}
                                        leftIcon={<Text fontSize="sm">{expandedSubItem === `${userGroup.username}-${dayGroup.date}` ? "▼" : "▶"}</Text>}
                                    >
                                        {formatDateForDisplay(dayGroup.date)} ({dayGroup.actionCount} actions)
                                    </Button>

                                    {expandedSubItem === `${userGroup.username}-${dayGroup.date}` && (
                                        <VStack align="stretch" spacing={2} mt={3}>
                                            {dayGroup.actions
                                                .slice()
                                                .sort((a, b) => b.date.localeCompare(a.date))
                                                .map((action, idx) => (
                                                    <HStack key={idx} align="center" bg="#2d3748" p={3} borderRadius="md">
                                                        <Image
                                                            src={action.imageUrl}
                                                            alt={action.description}
                                                            boxSize="60px"
                                                            borderRadius="md"
                                                            fallbackSrc="/placeholder-image.png"
                                                        />
                                                        <Box flex={1}>
                                                            <HStack>
                                                                <Text fontSize="sm" color="orange.300" fontWeight="bold">
                                                                    {formatTimeForDisplay(action.date)}
                                                                </Text>
                                                                <Badge colorScheme="purple" variant="outline" fontSize="xs">
                                                                    {action.actionType}
                                                                </Badge>
                                                            </HStack>
                                                            <Text fontSize="sm" color="white">{action.description}</Text>
                                                        </Box>
                                                    </HStack>
                                                ))}
                                        </VStack>
                                    )}
                                </Box>
                            ))}
                        </VStack>
                    )}
                </Box>
            ))}
        </VStack>
    );

    return (
        <Flex bg="#101114" color="#fff" minH="100vh" direction="column" p={6}>
            <Box flex="1">
                <Heading size="lg" mb={6} color="cyan.300">
                    Actions Dashboard
                    {pagination && (
                        <Text as="span" fontSize="md" color="gray.400" ml={2}>
                            ({groupBy === 'day' ? `${pagination.totalDays} days` : `${pagination.totalUsers} users`}, {pagination.totalActions} total actions)
                        </Text>
                    )}
                </Heading>

                {/* View Toggle */}
                <ButtonGroup mb={6} isAttached variant="outline">
                    <Button
                        colorScheme={groupBy === "user-day" ? "cyan" : "gray"}
                        bg={groupBy === "user-day" ? "#4fd1c7" : "transparent"}
                        color={groupBy === "user-day" ? "#1a202c" : "gray.300"}
                        onClick={() => setGroupBy("user-day")}
                        _hover={{ bg: groupBy === "user-day" ? "#38b2ac" : "#2d3748" }}
                    >
                        By User → Days
                    </Button>
                    <Button
                        colorScheme={groupBy === "day" ? "cyan" : "gray"}
                        bg={groupBy === "day" ? "#4fd1c7" : "transparent"}
                        color={groupBy === "day" ? "#1a202c" : "gray.300"}
                        onClick={() => setGroupBy("day")}
                        _hover={{ bg: groupBy === "day" ? "#38b2ac" : "#2d3748" }}
                    >
                        By Day → Users
                    </Button>
                </ButtonGroup>

                {/* Render appropriate view */}
                {groupBy === "day" ? renderDayView() : renderUserDayView()}

                {/* Infinite scroll trigger */}
                {hasMore && (
                    <div ref={actionsEndRef} style={{ height: '20px' }} />
                )}

                {isLoading && (
                    <Flex justify="center" p={4}>
                        <Spinner size="md" color="cyan.300" />
                    </Flex>
                )}

                {!hasMore && dataGroups.length > 0 && (
                    <Box fontSize="sm" mt={4} textAlign="center" color="gray.400">
                        Showing all {groupBy === 'day' ? `${pagination?.totalDays || dataGroups.length} days` : `${pagination?.totalUsers || dataGroups.length} users`}
                    </Box>
                )}

                {dataGroups.length === 0 && !initialLoading && (
                    <Box fontSize="sm" mt={4} textAlign="center" color="gray.400">
                        No actions found
                    </Box>
                )}
            </Box>
        </Flex>
    );
}
