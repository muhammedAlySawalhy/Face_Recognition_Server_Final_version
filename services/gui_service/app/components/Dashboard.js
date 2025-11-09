import React, { useContext, useState, useEffect } from "react";
import {
  Box,
  Flex,
  Heading,
  Spinner,
  List,
  ListItem,
  Badge,
  Input,
  Select,
  Text,
  Grid,
  GridItem,
  useBreakpointValue,
  VisuallyHidden
} from "@chakra-ui/react";
import { Doughnut } from "react-chartjs-2";
import { useInView } from "react-intersection-observer";
import { useLiveClients, useNotificationsData } from "../DashboardContext";
import ConnectionToInternetError from "./ConnectionToInternetError";
import { Chart, ArcElement } from "chart.js";
Chart.register(ArcElement);

const PAGE_SIZE = 8;

// Extract prefix (first two chars) from username for region filtering
function getGovernmentPrefix(username) {
  return typeof username === "string"
    ? username.substring(0, 2).toLowerCase()
    : "";
}

// Government mapping for accessibility
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

export default function Dashboard() {
  const { active, deactivated, loading, connectingError } = useLiveClients();
  const { notifications } = useNotificationsData();

  // Responsive grid template
  const gridTemplate = useBreakpointValue({
    base: "1fr",
    md: "1fr 1fr",
    lg: "2fr 1fr",
    xl: "2fr 1fr 1fr"
  });

  // Filters (same as Monitoring section)
  const [search, setSearch] = useState("");
  const [governmentFilter, setGovernmentFilter] = useState("");

  // Infinite scroll state for notifications
  const [notificationsVisible, setNotificationsVisible] = useState(PAGE_SIZE);

  // Observer for notifications
  const { ref: notificationsRef, inView: notificationsInView } = useInView({ threshold: 0.1 });

  useEffect(() => {
    if (notificationsInView && notificationsVisible < notifications.length) {
      setNotificationsVisible(c => Math.min(c + PAGE_SIZE, notifications.length));
    }
  }, [notificationsInView, notificationsVisible, notifications.length]);

  // Process and filter users (same logic as Monitoring)
  const formatClients = (clients, status) =>
    (clients || []).map((u) => ({
      ...(typeof u === "string" ? { username: u } : u),
      status,
    }));

  const activeClients = formatClients(active, "Online");
  const deactivatedClients = formatClients(deactivated, "Offline");
  const errorClients = formatClients(connectingError, "Connection Error");
  const allClients = [...activeClients, ...deactivatedClients, ...errorClients];

  const allPrefixes = Array.from(
    Object.entries(GOV_NAMES).map(([key, value]) => key))

  let filteredClients = allClients
    .filter(
      (u) => !governmentFilter || getGovernmentPrefix(u.username) === governmentFilter
    )
    .filter(
      (u) =>
        !search ||
        (u.username && u.username.toLowerCase().includes(search.toLowerCase()))
    );

  // Chart data with filtered results
  const onlineCount = filteredClients.filter((u) => u.status === "Online").length;
  const offlineCount = filteredClients.filter((u) => u.status === "Offline").length;
  const errorCount = filteredClients.filter((u) => u.status === "Connection Error").length;
  const total = onlineCount + offlineCount + errorCount;

  // More accessible chart with better colors and labels
  const statusChart = {
    labels: ["Online Users", "Offline Users", "Connection Errors"],
    datasets: [{
      data: [onlineCount, offlineCount, errorCount],
      backgroundColor: ["#48bb78", "#f56565", "#ed8936"],
      borderColor: ["#38a169", "#e53e3e", "#dd6b20"],
      borderWidth: 2,
      hoverBorderWidth: 3
    }]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          color: 'white',
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.label}: ${ctx.raw} users (${total ? Math.round((ctx.raw / total) * 100) : 0}%)`
        },
        backgroundColor: 'rgba(0,0,0,0.8)',
        titleColor: 'white',
        bodyColor: 'white'
      }
    },
    accessibility: {
      announceNewData: {
        enabled: true
      }
    }
  };

  // Reset filters on data change
  useEffect(() => {
    setNotificationsVisible(PAGE_SIZE);
  }, [search, governmentFilter]);

  if (loading) {
    return (
      <Flex justify="center" align="center" minH="50vh">
        <Spinner size="xl" color="blue.500" thickness="4px" />
        <VisuallyHidden>Loading dashboard data</VisuallyHidden>
      </Flex>
    );
  }

  // Common card styling to enforce consistent look and prevent overflow
  const cardProps = {
    bg: "#181c24",
    p: 4,
    borderRadius: "md",
    border: "1px solid",
    borderColor: "#2a2f3a",
    overflow: "hidden",
  };

  return (
    <Box maxW="7xl" mx="auto" px={{ base: 2, md: 4 }}>
      <Heading
        size="lg"
        mb={6}
        textAlign="center"
        fontWeight="bold"
        color="white"
        as="h1"
      >
        Face Recognition Dashboard
      </Heading>

      {/* Filters Section - Same as Monitoring */}
      <Box mb={6} bg="#181c24" p={4} borderRadius="md">
        <Heading size="md" mb={4} color="white">Filters & Search</Heading>
        <Flex gap={4} direction={{ base: "column", md: "row" }} align="start">
          <Box>
            <Text fontSize="sm" color="gray.300" mb={2}>Government Region</Text>
            <Select
              placeholder="All governments"
              value={governmentFilter}
              onChange={(e) => setGovernmentFilter(e.target.value)}
              w="200px"
              bg="#222"
              color="white"
              borderColor="#444"
              _hover={{ borderColor: "#666" }}
              _focus={{ borderColor: "#0078d4", boxShadow: "0 0 0 1px #0078d4" }}
            >
              {allPrefixes.map((prefix) => (
                <option value={prefix} key={prefix} style={{ backgroundColor: "#222", color: "white" }}>
                  {GOV_NAMES[prefix] || prefix.toUpperCase()}
                </option>
              ))}
            </Select>
          </Box>
          <Box>
            <Text fontSize="sm" color="gray.300" mb={2}>Search Username</Text>
            <Input
              placeholder="Search by username..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              w="250px"
              bg="#222"
              color="white"
              borderColor="#444"
              _hover={{ borderColor: "#666" }}
              _focus={{ borderColor: "#0078d4", boxShadow: "0 0 0 1px #0078d4" }}
              _placeholder={{ color: "gray.400" }}
            />
          </Box>
          <Box alignSelf="end">
            <Text fontSize="sm" color="gray.300" mb={2}>Results</Text>
            <Text color="blue.300" fontWeight="bold">
              {filteredClients.length} users found
            </Text>
          </Box>
        </Flex>
      </Box>

      {/* Main Grid Layout */}
      <Grid
        templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", xl: "repeat(3, 1fr)" }}
        gap={6}
        mb={6}
        alignItems="stretch"
      >
        {/* Notifications */}
        <GridItem>
          <Box {...cardProps} h="400px">
            <Heading size="md" mb={4} color="white" as="h2">
              Recent Activity
              <Badge ml={2} colorScheme="blue" fontSize="xs">
                {notifications.length}
              </Badge>
            </Heading>
            <Box h="320px" overflowY="auto" bg="#222" p={3} borderRadius="md" border="1px solid" borderColor="#2a2f3a">
              <List spacing={2}>
                {notifications.slice(0, notificationsVisible).map((n, i) => (
                  <ListItem
                    key={n.time + n.user + i}
                    bg="#333"
                    p={3}
                    borderRadius="md"
                    mb={2}
                    _hover={{ bg: "#444" }}
                    transition="background 0.2s"
                  >
                    <Flex align="center" gap={3}>
                      <Badge
                        colorScheme={n.type === "activated" ? "green" : "red"}
                        fontSize="xs"
                        px={2}
                        py={1}
                      >
                        {n.user}
                      </Badge>
                      <Text fontSize="sm" color="gray.200" flex="1">
                        {n.action}
                      </Text>
                      <Text fontSize="xs" color="gray.400">
                        {n.time}
                      </Text>
                    </Flex>
                  </ListItem>
                ))}
              </List>
              {notificationsVisible < notifications.length && <div ref={notificationsRef} />}
              {notificationsVisible >= notifications.length && notifications.length > 0 && (
                <Box fontSize="sm" mt={3} textAlign="center" color="gray.400">
                  All notifications loaded
                </Box>
              )}
              {notifications.length === 0 && (
                <Flex justify="center" align="center" h="200px" direction="column">
                  <Text color="gray.400" fontSize="md">No recent activity</Text>
                  <Text color="gray.500" fontSize="sm" mt={1}>
                    User activity will appear here
                  </Text>
                </Flex>
              )}
            </Box>
          </Box>
        </GridItem>

        {/* Connection Status Summary */}
        <GridItem>
          <Box {...cardProps} h="400px">
            <Heading size="md" mb={4} color="white" as="h2">
              Connection Status
            </Heading>
            <Box h="calc(100% - 40px)" overflow="hidden">
              <ConnectionToInternetError
                variant="summary"
                title="Connection Status"
              />
            </Box>
          </Box>
        </GridItem>

        {/* User Status Chart */}
        <GridItem>
          <Box {...cardProps} h="400px">
            <Heading size="md" mb={4} color="white" as="h2">
              User Status Overview
            </Heading>
            <Box h="250px" position="relative" role="img" aria-label="User status doughnut chart showing counts of online, offline, and connection error users">
              <Doughnut data={statusChart} options={chartOptions} />
            </Box>
            <Box mt={4}>
              <Grid templateColumns="repeat(3, 1fr)" gap={2} textAlign="center">
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="green.400">
                    {onlineCount}
                  </Text>
                  <Text fontSize="xs" color="gray.400">Online</Text>
                </Box>
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="red.400">
                    {offlineCount}
                  </Text>
                  <Text fontSize="xs" color="gray.400">Offline</Text>
                </Box>
                <Box>
                  <Text fontSize="lg" fontWeight="bold" color="orange.400">
                    {errorCount}
                  </Text>
                  <Text fontSize="xs" color="gray.400">Errors</Text>
                </Box>
              </Grid>
            </Box>
          </Box>
        </GridItem>
      </Grid>

      {/* Connection Error Analysis Section */}
      <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap={6} mb={6} alignItems="stretch">
        <GridItem>
          <Box {...cardProps} h={{ base: "auto", md: "380px" }}>
            <Heading size="md" mb={4} color="white" as="h2">
              Internet Connection Errors by Region
            </Heading>
            <Box h={{ base: "260px", md: "calc(100% - 40px)" }}>
              <ConnectionToInternetError
                variant="chart"
                title="Internet Connection Errors by Region"
                showDetails={true}
              />
            </Box>
          </Box>
        </GridItem>
        <GridItem>
          <Box {...cardProps} h={{ base: "auto", md: "380px" }}>
            <Heading size="md" mb={4} color="white" as="h2">
              Error Distribution
            </Heading>
            <Box h={{ base: "260px", md: "calc(100% - 40px)" }} role="img" aria-label="Doughnut chart showing distribution of connection errors by region">
              <ConnectionToInternetError
                variant="doughnut"
                title="Error Distribution"
              />
            </Box>
          </Box>
        </GridItem>
      </Grid>

      {/* Detailed Connection Error Table */}
      <Box {...cardProps}>
        <Heading size="md" mb={4} color="white" as="h2">
          Recent Connection Errors - Detailed View
        </Heading>
        <Box overflowX="auto" aria-label="Table of recent connection errors">
          <ConnectionToInternetError
            variant="table"
            title="Recent Connection Errors - Detailed View"
          />
        </Box>
      </Box>
    </Box>
  );
}