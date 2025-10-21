import React, { useContext, useState, useEffect } from "react";
import {
  Box,
  Flex,
  Heading,
  Input,
  Table,
  Tbody,
  Tr,
  Td,
  Th,
  Thead,
  Badge,
  Spinner,
  Select,
  Text,
  Grid,
  GridItem,
  useBreakpointValue,
  VisuallyHidden,
} from "@chakra-ui/react";
import { Doughnut } from "react-chartjs-2";
import { useInView } from "react-intersection-observer";
import { useLiveClients } from "../DashboardContext";
import ConnectionToInternetError from "./ConnectionToInternetError";
import { Chart, ArcElement } from "chart.js";
Chart.register(ArcElement);

const PAGE_SIZE = 12;

function statusColor(status) {
  switch (status) {
    case "Online":
      return "green";
    case "Offline":
      return "red";
    case "Paused":
      return "yellow";
    case "Blocked":
      return "gray";
    default:
      return "blue";
  }
}

// Extract prefix (first two chars) from username
function getGovernmentPrefix(username) {
  return typeof username === "string"
    ? username.substring(0, 2).toLowerCase()
    : "";
}

// Government mapping for better accessibility
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

export default function MonitoringDashboard() {
  // State for expanded rows
  const [expandedUser, setExpandedUser] = useState(null);
  const { active, deactivated, fetchDashboardData, loading, connectingError } = useLiveClients();

  // Responsive layout
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Filters
  const [search, setSearch] = useState("");
  const [governmentFilter, setGovernmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState(""); // New status filter

  // Combine active and deactivated (and assign status)
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
      (u) => !statusFilter || u.status === statusFilter
    )
    .filter(
      (u) =>
        !search ||
        (u.username && u.username.toLowerCase().includes(search.toLowerCase()))
    );



  // Group users by username
  let groupedClients = filteredClients.reduce((acc, u) => {
    const uname = u.username || "";
    if (!acc[uname]) acc[uname] = [];
    acc[uname].push(u);
    return acc;
  }, {});
  // Array of grouped usernames
  const groupedUsernames = Object.keys(groupedClients);

  const onlineCount = filteredClients.filter((u) => u.status === "Online").length;
  const offlineCount = filteredClients.filter((u) => u.status === "Offline").length;
  const errorCount = filteredClients.filter((u) => u.status === "Connection Error").length;

  const userStatusChart = {
    labels: ["Online", "Offline", "Connection Errors"],
    datasets: [
      {
        data: [onlineCount, offlineCount, errorCount],
        backgroundColor: ["#48bb78", "#f56565", "#ed8936"],
        borderColor: ["#38a169", "#e53e3e", "#dd6b20"],
        borderWidth: 2,
      },
    ],
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
          padding: 15,
          usePointStyle: true,
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.8)',
        titleColor: 'white',
        bodyColor: 'white'
      }
    }
  };

  // Infinite scroll for table
  const [clientsVisible, setClientsVisible] = useState(PAGE_SIZE);
  const { ref: clientsRef, inView: clientsInView } = useInView({ threshold: 0.1 });
  useEffect(() => {
    if (clientsInView && clientsVisible < groupedUsernames.length) {
      setClientsVisible((c) => Math.min(c + PAGE_SIZE, groupedUsernames.length));
    }
  }, [clientsInView, clientsVisible, groupedUsernames.length]);
  useEffect(() => {
    setClientsVisible(PAGE_SIZE); // Reset on filter/search change
  }, [search, governmentFilter, statusFilter]);

  if (loading) {
    return (
      <Flex justify="center" align="center" minH="50vh">
        <Spinner size="xl" color="blue.500" thickness="4px" />
        <VisuallyHidden>Loading monitoring data</VisuallyHidden>
      </Flex>
    );
  }

  const cardProps = {
    bg: "#181c24",
    p: 4,
    borderRadius: "md",
    border: "1px solid",
    borderColor: "#2a2f3a",
    overflow: "hidden",
  };

  return (
    <Flex bg="#101114" color="#fff" minH="100vh" direction="column" p={{ base: 2, md: 4 }}>
      <Box ml="0" p={0} flex="1" maxW="7xl" mx="auto" w="100%">
        {/* Header */}
        <Heading size="lg" mb={6} color="white" as="h1">
          Real-time Monitoring
        </Heading>

        {/* Enhanced Filters Section */}
        <Box mb={6} bg="#181c24" p={4} borderRadius="md">
          <Heading size="md" mb={4} color="white">Filters & Search</Heading>
          <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }} gap={4}>
            <Box>
              <Text fontSize="sm" color="gray.300" mb={2}>Government Region</Text>
              <Select
                placeholder="All Governments"
                value={governmentFilter}
                onChange={(e) => setGovernmentFilter(e.target.value)}
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
              <Text fontSize="sm" color="gray.300" mb={2}>Connection Status</Text>
              <Select
                placeholder="All Statuses"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                bg="#222"
                color="white"
                borderColor="#444"
                _hover={{ borderColor: "#666" }}
                _focus={{ borderColor: "#0078d4", boxShadow: "0 0 0 1px #0078d4" }}
              >
                <option value="Online" style={{ backgroundColor: "#222", color: "white" }}>Online</option>
                <option value="Offline" style={{ backgroundColor: "#222", color: "white" }}>Offline</option>
                <option value="Connection Error" style={{ backgroundColor: "#222", color: "white" }}>Connection Error</option>
              </Select>
            </Box>
            <Box>
              <Text fontSize="sm" color="gray.300" mb={2}>Search Username</Text>
              <Input
                placeholder="Search by username..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
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
          </Grid>
        </Box>
        {/* Users Monitoring Table */}
        <Box mb={8}>
          <Box {...cardProps}>
            <Heading size="md" mb={4} color="white" as="h2">
              Active Users Monitoring
              <Badge ml={3} colorScheme="blue" fontSize="sm">
                {groupedUsernames.length} users
              </Badge>
            </Heading>
            {groupedUsernames.length > 0 ? (
              <>
                <Box overflowX="auto">
                  <Table variant="simple" size="sm">
                    <Thead>
                      <Tr>
                        <Th color="white" fontSize="sm">Username</Th>
                        <Th color="white" fontSize="sm">Government</Th>
                        <Th color="white" fontSize="sm">Status</Th>
                        <Th color="white" fontSize="sm">Last Activity</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {groupedUsernames.slice(0, clientsVisible).map((uname) => {
                        const userGroup = groupedClients[uname];
                        const mainUser = userGroup[0];
                        const govPrefix = getGovernmentPrefix(uname);
                        const govName = GOV_NAMES[govPrefix] || govPrefix.toUpperCase();

                        return (
                          <Tr
                            key={uname}
                            _hover={{ bg: "#333" }}
                            transition="background 0.2s"
                          >
                            <Td color="white" fontFamily="mono" fontSize="sm">
                              {uname}
                            </Td>
                            <Td color="gray.300" fontSize="sm">
                              {govName}
                            </Td>
                            <Td>
                              <Badge
                                colorScheme={statusColor(mainUser.status)}
                                fontSize="xs"
                                px={2}
                                py={1}
                              >
                                {mainUser.status}
                              </Badge>
                            </Td>
                            <Td color="gray.400" fontSize="xs">
                              {new Date().toLocaleTimeString()}
                            </Td>
                          </Tr>
                        );
                      })}
                    </Tbody>
                  </Table>
                </Box>
                {clientsVisible < groupedUsernames.length && <div ref={clientsRef} />}
                {clientsVisible >= groupedUsernames.length && groupedUsernames.length > 0 && (
                  <Box fontSize="sm" mt={3} textAlign="center" color="gray.400">
                    All users loaded ({groupedUsernames.length} total)
                  </Box>
                )}
              </>
            ) : (
              <Flex justify="center" align="center" h="200px" direction="column">
                <Text color="gray.400" fontSize="md">No users found</Text>
                <Text color="gray.500" fontSize="sm" mt={1}>
                  Try adjusting your filters
                </Text>
              </Flex>
            )}
          </Box>
        </Box>

        {/* Analytics Grid */}
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap={6} mb={6} alignItems="stretch">
          <GridItem>
            <Box {...cardProps} h={{ base: "auto", md: "380px" }}>
              <Heading size="md" mb={4} color="white" as="h2">
                Internet Connection Errors by Government
              </Heading>
              <Box h={{ base: "260px", md: "calc(100% - 40px)" }}>
                <ConnectionToInternetError
                  variant="chart"
                  title="Internet Connection Errors by Government"
                  showDetails={true}
                />
              </Box>
            </Box>
          </GridItem>
          <GridItem>
            <Box {...cardProps} h="350px">
              <Heading size="md" mb={4} color="white" as="h2">
                Status Distribution
              </Heading>
              <Box h="220px" position="relative" role="img" aria-label="User connection status distribution">
                <Doughnut data={userStatusChart} options={chartOptions} />
              </Box>
              <Grid templateColumns="repeat(3, 1fr)" gap={2} mt={4} textAlign="center">
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
          </GridItem>
        </Grid>

        {/* Connection Error Detailed Analysis */}
        <Box {...cardProps}>
          <Heading size="md" mb={4} color="white" as="h2">
            Connection Error Distribution by Region
          </Heading>
          <Box role="img" aria-label="Doughnut chart showing connection error distribution by region">
            <ConnectionToInternetError
              variant="doughnut"
              title="Connection Error Distribution by Region"
            />
          </Box>
        </Box>
      </Box>
    </Flex>
  );
}