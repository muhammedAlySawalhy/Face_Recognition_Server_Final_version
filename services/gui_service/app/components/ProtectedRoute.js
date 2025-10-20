'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Spinner,
  VStack,
  Text,
  Alert,
  AlertIcon,
  Button
} from '@chakra-ui/react';

const ProtectedRoute = ({ children, requireAdmin = true }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const router = useRouter();

  useEffect(() => {
    checkAuthentication();
  }, []);

  const checkAuthentication = async () => {
    try {
      const response = await fetch('/api/auth/verify');
      const result = await response.json();

      if (result.success && result.isAuthenticated) {
        if (requireAdmin && result.role !== 'admin') {
          setAuthError('Admin access required');
          setIsAuthenticated(false);
        } else {
          setIsAuthenticated(true);
        }
      } else {
        setAuthError('Authentication required');
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Authentication check failed:', error);
      setAuthError('Authentication check failed');
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = () => {
    router.push('/admin/login');
  };

  const handleHome = () => {
    router.push('/');
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <Box
        bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.300" thickness="4px" />
          <Text color="white" fontSize="lg">
            Verifying access permissions...
          </Text>
        </VStack>
      </Box>
    );
  }

  // Show error message if authentication failed
  if (!isAuthenticated || authError) {
    return (
      <Box
        bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
        px={4}
      >
        <VStack spacing={6} maxW="md" textAlign="center">
          <Alert status="warning" borderRadius="lg">
            <AlertIcon />
            <Box>
              <Text fontWeight="bold">Access Denied</Text>
              <Text fontSize="sm" mt={1}>
                {authError || 'You need to login to access this page'}
              </Text>
            </Box>
          </Alert>

          <VStack spacing={3}>
            <Text color="white" fontSize="lg">
              Admin Authentication Required
            </Text>
            <Text color="gray.300" fontSize="sm">
              Please login with admin credentials to access the management panel.
            </Text>
          </VStack>

          <VStack spacing={3} w="full">
            <Button
              variant="mirando"
              size="lg"
              onClick={handleLogin}
              w="full"
              _hover={{ transform: 'translateY(-1px)' }}
            >
              🔐 Go to Login
            </Button>

            <Button
              variant="outline"
              size="md"
              onClick={handleHome}
              color="white"
              borderColor="gray.400"
              _hover={{
                bg: "whiteAlpha.200",
                borderColor: "white",
                transform: 'translateY(-1px)'
              }}
            >
              ← Back to Home
            </Button>
          </VStack>
        </VStack>
      </Box>
    );
  }

  // If authenticated, render the protected content
  return <>{children}</>;
};

export default ProtectedRoute;