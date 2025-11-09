import React, { useContext } from "react";
import {
    Box,
    Heading,
    Text,
    Flex,
    Badge,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Spinner,
} from "@chakra-ui/react";
import { Bar, Doughnut } from "react-chartjs-2";
import { useLiveClients } from "../DashboardContext";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement
);

// Extract government prefix from username
function getGovernmentPrefix(username) {
    return typeof username === "string" ? username.substring(0, 2).toLowerCase() : "";
}

// Government prefix to full name mapping
const GOV_NAMES = {
    "ci": "Cairo",
    "gz": "Giza",
    "ax": "Alexandria",
    "an": "Aswan",
    "lx": "Luxor",
    "kh": "Kafr El Sheikh",
    "mn": "Minya",
    "bh": "Beheira",
    "bn": "Beni Suef",
    "dk": "Dakahlia",
    "dm": "Damietta",
    "fj": "Fayoum",
    "ga": "Gharbia",
    "im": "Ismailia",
    "mo": "Monufia",
    "mt": "Matrouh",
    "ns": "North Sinai",
    "pr": "Port Said",
    "ql": "Qalyubia",
    "qn": "Qena",
    "rd": "Red Sea",
    "sh": "Sohag",
    "ss": "South Sinai",
    "sr": "Sharqia",
    "sz": "Suez",
    "au": "Asyut"
};

export default function ConnectionToInternetError({
    variant = "chart", // "chart", "doughnut", "table", "summary"
    title = "Internet Connection Errors",
    showDetails = false
}) {
    const { connectingError, loading } = useLiveClients();

    if (loading) {
        return (
            <Box bg="#181c24" p={4} borderRadius="md">
                <Heading size="sm" mb={4} color="white">
                    {title}
                </Heading>
                <Flex justify="center" align="center" h="200px">
                    <Spinner size="lg" color="red.400" />
                </Flex>
            </Box>
        );
    }

    // Process connection error data
    const errorClients = connectingError || [];
    const totalErrors = errorClients.length;

    // Group by government
    const errorsByGov = errorClients.reduce((acc, client) => {
        const username = typeof client === "string" ? client : client.username;
        const prefix = getGovernmentPrefix(username);
        const govName = GOV_NAMES[prefix] || prefix.toUpperCase();

        if (!acc[govName]) {
            acc[govName] = [];
        }
        acc[govName].push({ username, prefix });
        return acc;
    }, {});

    const govLabels = Object.keys(errorsByGov);
    const govCounts = govLabels.map(gov => errorsByGov[gov].length);

    // Chart colors
    const chartColors = [
        "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4", "#ffeaa7",
        "#dda0dd", "#98d8c8", "#f7dc6f", "#bb8fce", "#85c1e9"
    ];

    // Bar Chart Data
    const barChartData = {
        labels: govLabels,
        datasets: [
            {
                label: "Connection Errors",
                data: govCounts,
                backgroundColor: chartColors.slice(0, govLabels.length),
                borderColor: chartColors.slice(0, govLabels.length).map(color => color + "cc"),
                borderWidth: 1,
            },
        ],
    };

    const barChartOptions = {
        responsive: true,
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: false,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    color: "white",
                    stepSize: 1,
                },
                grid: {
                    color: "#333",
                },
            },
            x: {
                ticks: {
                    color: "white",
                    maxRotation: 45,
                },
                grid: {
                    color: "#333",
                },
            },
        },
    };

    // Doughnut Chart Data
    const doughnutData = {
        labels: govLabels,
        datasets: [
            {
                data: govCounts,
                backgroundColor: chartColors.slice(0, govLabels.length),
                borderColor: "#181c24",
                borderWidth: 2,
            },
        ],
    };

    const doughnutOptions = {
        responsive: true,
        plugins: {
            legend: {
                position: "bottom",
                labels: {
                    color: "white",
                    font: {
                        size: 10,
                    },
                },
            },
        },
    };

    // Render based on variant
    if (totalErrors === 0) {
        return (
            <Box bg="#181c24" p={4} borderRadius="md">
                <Heading size="sm" mb={4} color="white">
                    {title}
                </Heading>
                <Flex justify="center" align="center" h="200px" direction="column">
                    <Text color="green.400" fontSize="lg" fontWeight="bold">
                        ✅ No Connection Errors
                    </Text>
                    <Text color="gray.400" fontSize="sm" mt={2}>
                        All clients are connecting properly
                    </Text>
                </Flex>
            </Box>
        );
    }

    if (variant === "summary") {
        return (
            <Box bg="#181c24" p={4} borderRadius="md">
                <Heading size="sm" mb={4} color="white">
                    {title}
                </Heading>
                <Flex align="center" gap={4}>
                    <Box>
                        <Text fontSize="2xl" fontWeight="bold" color="red.400">
                            {totalErrors}
                        </Text>
                        <Text fontSize="sm" color="gray.400">
                            Connection Errors
                        </Text>
                    </Box>
                    <Box>
                        <Text fontSize="lg" color="yellow.400">
                            {govLabels.length}
                        </Text>
                        <Text fontSize="sm" color="gray.400">
                            Affected Regions
                        </Text>
                    </Box>
                </Flex>
            </Box>
        );
    }

    if (variant === "table") {
        return (
            <Box bg="#181c24" p={4} borderRadius="md">
                <Heading size="sm" mb={4} color="white">
                    {title}
                </Heading>
                <Table variant="simple" size="sm">
                    <Thead>
                        <Tr>
                            <Th color="white">Username</Th>
                            <Th color="white">Government</Th>
                            <Th color="white">Status</Th>
                        </Tr>
                    </Thead>
                    <Tbody>
                        {errorClients.slice(0, 10).map((client, index) => {
                            const username = typeof client === "string" ? client : client.username;
                            const prefix = getGovernmentPrefix(username);
                            const govName = GOV_NAMES[prefix] || prefix.toUpperCase();

                            return (
                                <Tr key={`${username}-${index}`}>
                                    <Td color="white">{username}</Td>
                                    <Td color="white">{govName}</Td>
                                    <Td>
                                        <Badge colorScheme="red" size="sm">
                                            Connection Error
                                        </Badge>
                                    </Td>
                                </Tr>
                            );
                        })}
                    </Tbody>
                </Table>
                {errorClients.length > 10 && (
                    <Text fontSize="sm" color="gray.400" mt={2} textAlign="center">
                        Showing 10 of {totalErrors} connection errors
                    </Text>
                )}
            </Box>
        );
    }

    if (variant === "doughnut") {
        return (
            <Box bg="#181c24" p={4} borderRadius="md">
                <Heading size="sm" mb={4} color="white">
                    {title}
                </Heading>
                <Box h="300px">
                    <Doughnut data={doughnutData} options={doughnutOptions} />
                </Box>
                <Text fontSize="sm" color="gray.400" textAlign="center" mt={2}>
                    Total: {totalErrors} connection errors
                </Text>
            </Box>
        );
    }

    // Default: Bar Chart
    return (
        <Box bg="#181c24" p={4} borderRadius="md">
            <Heading size="sm" mb={4} color="white">
                {title}
            </Heading>
            <Box h="300px">
                <Bar data={barChartData} options={barChartOptions} />
            </Box>
            {showDetails && (
                <Box mt={4}>
                    <Text fontSize="sm" color="gray.400" mb={2}>
                        Breakdown by Government:
                    </Text>
                    <Flex gap={2} flexWrap="wrap">
                        {govLabels.map((gov, index) => (
                            <Badge key={gov} colorScheme="red" size="sm">
                                {gov}: {govCounts[index]}
                            </Badge>
                        ))}
                    </Flex>
                </Box>
            )}
            <Text fontSize="sm" color="gray.400" textAlign="center" mt={2}>
                Total: {totalErrors} clients with connection errors
            </Text>
        </Box>
    );
}
