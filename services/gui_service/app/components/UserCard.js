import React from "react";
import {
  Box,
  Avatar,
  Text,
  Stack,
  Button,
  Badge,
  Flex
} from "@chakra-ui/react";

export default function UserCard({ user, showActions }) {
  if (!user) return null;
  // Determine status from user object
  let status = "Pending";
  if (user.status) {
    if (user.status.toLowerCase() === "blocked") status = "Blocked";
    else if (user.status.toLowerCase() === "approved") status = "Approved";
    else if (user.status.toLowerCase() === "pending") status = "Pending";
    else status = user.status;
  }
  // Optionally, check for blocked/approved flags
  if (user.blocked) status = "Blocked";
  if (user.approved) status = "Approved";

  return (
    <Box
      bg="#20232a"
      borderRadius="md"
      boxShadow="md"
      p={4}
      display="flex"
      flexDirection="column"
      alignItems="center"
    >
      <Avatar
        size="xl"
        name={user.name || user.username}
        src={user.photo_url}
        mb={3}
      />
      <Stack spacing={1} align="center" mb={2}>
        <Text fontWeight="bold" fontSize="lg">{user.name || "-"}</Text>
        <Badge colorScheme="cyan">{user.username}</Badge>
        <Badge colorScheme={status === "Blocked" ? "red" : status === "Approved" ? "green" : "yellow"}>
          {status}
        </Badge>
        <Text fontSize="sm" color="gray.400">
          National ID: {user.national_id || "-"}
        </Text>
        <Text fontSize="sm" color="gray.400">
          Government: {user.government || "-"}
        </Text>
        <Text fontSize="sm" color="gray.400">
          Department: {user.department || "-"}
        </Text>
        <Text fontSize="sm" color="gray.400">
          Role: {user.role || "-"}
        </Text>
      </Stack>
      {showActions && (
        <Flex mt={2} gap={2}>
          <Button size="sm" colorScheme="green">Approve</Button>
          <Button size="sm" colorScheme="red">Block</Button>
        </Flex>
      )}
    </Box>
  );
}