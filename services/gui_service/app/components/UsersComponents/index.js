import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Box,
    Button,
    HStack,
    Text,
    IconButton,
    Select,
    Input,
    VStack,
    Flex,
    Badge,
    useToast,
    Spinner,
    Center
} from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';

// Pagination Component with page buttons
export const PaginationComponent = ({
    currentPage,
    totalItems,
    itemsPerPage = 50,
    onPageChange,
    maxVisiblePages = 7
}) => {
    const totalPages = Math.ceil(totalItems / itemsPerPage);

    // Calculate which page numbers to show
    const getVisiblePages = () => {
        if (totalPages <= maxVisiblePages) {
            return Array.from({ length: totalPages }, (_, i) => i + 1);
        }

        const half = Math.floor(maxVisiblePages / 2);
        let start = Math.max(1, currentPage - half);
        let end = Math.min(totalPages, start + maxVisiblePages - 1);

        // Adjust start if we're near the end
        if (end - start + 1 < maxVisiblePages) {
            start = Math.max(1, end - maxVisiblePages + 1);
        }

        return Array.from({ length: end - start + 1 }, (_, i) => start + i);
    };

    const visiblePages = getVisiblePages();
    const showFirstPage = visiblePages[0] > 1;
    const showLastPage = visiblePages[visiblePages.length - 1] < totalPages;
    const showFirstEllipsis = visiblePages[0] > 2;
    const showLastEllipsis = visiblePages[visiblePages.length - 1] < totalPages - 1;

    if (totalPages <= 1) return null;

    return (
        <VStack spacing={4} align="center" py={6}>
            {/* Page info */}
            <Text fontSize="sm" color="gray.400">
                Page {currentPage} of {totalPages} ({totalItems} total items)
            </Text>

            {/* Pagination buttons */}
            <HStack spacing={1} wrap="wrap" justify="center">
                {/* Previous button */}
                <IconButton
                    icon={<ChevronLeftIcon />}
                    onClick={() => onPageChange(currentPage - 1)}
                    isDisabled={currentPage === 1}
                    size="sm"
                    variant="outline"
                    colorScheme="cyan"
                    bg="rgba(255,255,255,0.05)"
                    border="1px solid rgba(255,255,255,0.15)"
                    color="#00E5FF"
                    _hover={{ bg: "rgba(0,229,255,0.1)" }}
                    _disabled={{ opacity: 0.4, cursor: "not-allowed" }}
                />

                {/* First page */}
                {showFirstPage && (
                    <>
                        <Button
                            onClick={() => onPageChange(1)}
                            size="sm"
                            variant={currentPage === 1 ? "solid" : "outline"}
                            colorScheme="cyan"
                            bg={currentPage === 1 ? "#00E5FF" : "rgba(255,255,255,0.05)"}
                            color={currentPage === 1 ? "#101114" : "#00E5FF"}
                            border="1px solid rgba(255,255,255,0.15)"
                            _hover={{ bg: currentPage === 1 ? "#00B8D9" : "rgba(0,229,255,0.1)" }}
                        >
                            1
                        </Button>
                        {showFirstEllipsis && (
                            <Text color="gray.400" px={2}>...</Text>
                        )}
                    </>
                )}

                {/* Visible page numbers */}
                {visiblePages.map(page => (
                    <Button
                        key={page}
                        onClick={() => onPageChange(page)}
                        size="sm"
                        variant={currentPage === page ? "solid" : "outline"}
                        colorScheme="cyan"
                        bg={currentPage === page ? "#00E5FF" : "rgba(255,255,255,0.05)"}
                        color={currentPage === page ? "#101114" : "#00E5FF"}
                        border="1px solid rgba(255,255,255,0.15)"
                        _hover={{ bg: currentPage === page ? "#00B8D9" : "rgba(0,229,255,0.1)" }}
                        minW="40px"
                    >
                        {page}
                    </Button>
                ))}

                {/* Last page */}
                {showLastPage && (
                    <>
                        {showLastEllipsis && (
                            <Text color="gray.400" px={2}>...</Text>
                        )}
                        <Button
                            onClick={() => onPageChange(totalPages)}
                            size="sm"
                            variant={currentPage === totalPages ? "solid" : "outline"}
                            colorScheme="cyan"
                            bg={currentPage === totalPages ? "#00E5FF" : "rgba(255,255,255,0.05)"}
                            color={currentPage === totalPages ? "#101114" : "#00E5FF"}
                            border="1px solid rgba(255,255,255,0.15)"
                            _hover={{ bg: currentPage === totalPages ? "#00B8D9" : "rgba(0,229,255,0.1)" }}
                        >
                            {totalPages}
                        </Button>
                    </>
                )}

                {/* Next button */}
                <IconButton
                    icon={<ChevronRightIcon />}
                    onClick={() => onPageChange(currentPage + 1)}
                    isDisabled={currentPage === totalPages}
                    size="sm"
                    variant="outline"
                    colorScheme="cyan"
                    bg="rgba(255,255,255,0.05)"
                    border="1px solid rgba(255,255,255,0.15)"
                    color="#00E5FF"
                    _hover={{ bg: "rgba(0,229,255,0.1)" }}
                    _disabled={{ opacity: 0.4, cursor: "not-allowed" }}
                />
            </HStack>

            {/* Items per page selector */}
            <HStack>
                <Text fontSize="sm" color="gray.400">Items per page:</Text>
                <Select
                    size="sm"
                    value={itemsPerPage}
                    onChange={(e) => onPageChange(1, parseInt(e.target.value))}
                    bg="rgba(255,255,255,0.05)"
                    border="1px solid rgba(255,255,255,0.15)"
                    color="#00E5FF"
                    _hover={{ borderColor: "#00E5FF" }}
                    _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
                    maxW="80px"
                >
                    <option value={25} style={{ backgroundColor: '#2D3748', color: 'white' }}>25</option>
                    <option value={50} style={{ backgroundColor: '#2D3748', color: 'white' }}>50</option>
                    <option value={100} style={{ backgroundColor: '#2D3748', color: 'white' }}>100</option>
                </Select>
            </HStack>
        </VStack>
    );
};

// Enhanced Search Component that searches through all data
export const EnhancedSearchComponent = ({
    onSearchResults,
    status = "all",
    placeholder = "Search users by username, ID, or name...",
    searchEndpoint = "/api/users/read"
}) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const [allData, setAllData] = useState([]);
    const [searchResults, setSearchResults] = useState([]);
    const toast = useToast();

    // Fetch all data when component mounts or status changes
    const fetchAllData = useCallback(async () => {
        if (!searchTerm.trim()) return;

        setIsSearching(true);
        try {
            let allUsers = [];
            let page = 1;
            let hasMoreData = true;

            // Fetch all pages of data
            while (hasMoreData) {
                const params = new URLSearchParams({
                    status,
                    page: page.toString(),
                    limit: "100", // Fetch larger chunks for efficiency
                    paginated: "true"
                });

                const response = await fetch(`${searchEndpoint}?${params}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem("adminToken")}`
                    }
                });

                const result = await response.json();

                if (result.success && result.data) {
                    // Handle different status responses
                    let pageUsers = [];

                    if (status === "all") {
                        // Combine all status types
                        pageUsers = [
                            ...(result.data.pending?.users || result.data.pending || []),
                            ...(result.data.approved?.users || result.data.approved || []),
                            ...(result.data.rejected?.users || result.data.rejected || [])
                        ];
                    } else if (status === "approved") {
                        pageUsers = result.data.approved?.users || result.data.approved || [];
                    } else if (status === "pending") {
                        pageUsers = result.data.pending?.users || result.data.pending || [];
                    } else if (status === "blocked" || status === "rejected") {
                        pageUsers = result.data.rejected?.users || result.data.rejected || [];
                    }

                    allUsers = [...allUsers, ...pageUsers];

                    // Check if there's more data
                    const pagination = result.data[status === "blocked" ? "rejected" : status]?.pagination;
                    hasMoreData = pagination?.hasNextPage || false;
                    page++;

                    // Safety break to prevent infinite loops
                    if (page > 50) break;
                } else {
                    hasMoreData = false;
                }
            }

            setAllData(allUsers);

            // Perform search on all data
            if (searchTerm.trim()) {
                performSearch(allUsers, searchTerm);
            }
        } catch (error) {
            console.error('Error fetching search data:', error);
            toast({
                title: 'Search Error',
                description: 'Failed to fetch data for search',
                status: 'error',
                duration: 3000,
                isClosable: true,
            });
        } finally {
            setIsSearching(false);
        }
    }, [status, searchEndpoint, searchTerm, toast]);

    // Perform search on the data
    const performSearch = useCallback((data, term) => {
        if (!term.trim()) {
            setSearchResults([]);
            onSearchResults([], false);
            return;
        }

        const searchLower = term.toLowerCase();
        const filtered = data.filter(user => {
            return (
                user.username?.toLowerCase().includes(searchLower) ||
                user.name?.toLowerCase().includes(searchLower) ||
                user.nationalId?.toLowerCase().includes(searchLower) ||
                user.national_id?.toLowerCase().includes(searchLower) ||
                user.nationalID?.toLowerCase().includes(searchLower) ||
                user.department?.toLowerCase().includes(searchLower) ||
                user.government?.toLowerCase().includes(searchLower)
            );
        });

        setSearchResults(filtered);
        onSearchResults(filtered, true);
    }, [onSearchResults]);

    // Handle search input changes
    const handleSearchChange = (e) => {
        const value = e.target.value;
        setSearchTerm(value);

        if (!value.trim()) {
            setSearchResults([]);
            onSearchResults([], false);
            return;
        }

        // If we have data, search immediately
        if (allData.length > 0) {
            performSearch(allData, value);
        } else {
            // Fetch data and then search
            fetchAllData();
        }
    };

    // Clear search
    const clearSearch = () => {
        setSearchTerm('');
        setSearchResults([]);
        onSearchResults([], false);
    };

    return (
        <Box mb={6}>
            <Flex gap={3} align="center">
                <Box flex={1}>
                    <Input
                        placeholder={placeholder}
                        value={searchTerm}
                        onChange={handleSearchChange}
                        bg="rgba(255,255,255,0.05)"
                        border="1px solid rgba(255,255,255,0.15)"
                        color="#00E5FF"
                        _placeholder={{ color: "gray.400" }}
                        _hover={{ borderColor: "#00E5FF" }}
                        _focus={{ borderColor: "#00E5FF", boxShadow: "0 0 0 1px #00E5FF" }}
                        size="md"
                    />
                </Box>

                {searchTerm && (
                    <Button
                        onClick={clearSearch}
                        variant="outline"
                        colorScheme="gray"
                        size="md"
                        bg="rgba(255,255,255,0.05)"
                        border="1px solid rgba(255,255,255,0.15)"
                        color="gray.400"
                        _hover={{ bg: "rgba(255,255,255,0.1)" }}
                    >
                        Clear
                    </Button>
                )}
            </Flex>

            {/* Search status */}
            {isSearching && (
                <Center mt={3}>
                    <HStack>
                        <Spinner size="sm" color="#00E5FF" />
                        <Text fontSize="sm" color="gray.400">Searching all data...</Text>
                    </HStack>
                </Center>
            )}

            {searchTerm && !isSearching && (
                <Box mt={3}>
                    <Badge
                        colorScheme={searchResults.length > 0 ? "green" : "yellow"}
                        variant="solid"
                    >
                        {searchResults.length > 0
                            ? `Found ${searchResults.length} result(s)`
                            : 'No results found'
                        }
                    </Badge>
                </Box>
            )}
        </Box>
    );
};

// Hook for managing paginated data with enhanced search
export const usePaginatedData = (initialData = [], itemsPerPage = 50) => {
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(itemsPerPage);
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState([]);

    // Get current data (either search results or paginated data)
    const currentData = useMemo(() => {
        const dataToUse = isSearching ? searchResults : initialData;
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        return dataToUse.slice(startIndex, endIndex);
    }, [initialData, searchResults, isSearching, currentPage, pageSize]);

    // Get total items count
    const totalItems = isSearching ? searchResults.length : initialData.length;

    // Handle page change
    const handlePageChange = useCallback((page, newPageSize) => {
        if (newPageSize && newPageSize !== pageSize) {
            setPageSize(newPageSize);
            setCurrentPage(1); // Reset to first page when changing page size
        } else {
            setCurrentPage(page);
        }
    }, [pageSize]);

    // Handle search results
    const handleSearchResults = useCallback((results, searching) => {
        setSearchResults(results);
        setIsSearching(searching);
        setCurrentPage(1); // Reset to first page when searching
    }, []);

    // Reset page when data changes
    useEffect(() => {
        setCurrentPage(1);
    }, [initialData]);

    return {
        currentData,
        currentPage,
        pageSize,
        totalItems,
        isSearching,
        handlePageChange,
        handleSearchResults,
        searchResults
    };
};