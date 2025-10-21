'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Input,
  VStack,
  HStack,
  Text,
  useToast,
  Heading,
  Card,
  CardBody,
  FormControl,
  FormLabel,
  InputGroup,
  InputRightElement,
  IconButton,
  Center,
  Spinner,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

export default function AdminLoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const router = useRouter();
  const toast = useToast();

  useEffect(() => {
    checkExistingAuth();
  }, []);

  const checkExistingAuth = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      if (!token) {
        setIsCheckingAuth(false);
        return;
      }
      const response = await fetch('/api/auth/verify', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      const result = await response.json();

      if (result.success && result.isAuthenticated) {
        router.push('/admin');
        return;
      }
    } catch (error) {
      console.error('Auth check error:', error);
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      toast({
        title: "Error",
        description: "Please enter both username and password",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    setIsLoading(true);
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      const result = await response.json();
      if (result.success) {
        if (result.token) {
          localStorage.setItem('adminToken', result.token);
        }
        if (result.user) {
          localStorage.setItem('currentUser', JSON.stringify(result.user));
        }
        toast({
          title: "Success!",
          description: "Login successful. Redirecting...",
          status: "success",
          duration: 2000,
          isClosable: true,
        });
        setTimeout(() => {
          router.push('/admin');
        }, 1000);
      } else {
        throw new Error(result.error || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      toast({
        title: "Login Failed",
        description: error.message || "Invalid credentials. Please try again.",
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLogin(e);
    }
  };

  if (isCheckingAuth) {
    return (
      <Box
        bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.300" />
          <Text color="white">Checking authentication...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box
      bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      px={4}
    >
      <Card maxW="md" w="full" variant="mirando" shadow="2xl">
        <CardBody p={8}>
          <VStack spacing={6}>
            {/* Header */}
            <VStack spacing={2} textAlign="center">
              <Heading
                as="h1"
                size="lg"
                color="blue.600"
                fontWeight="bold"
              >
                Mirando Solutions
              </Heading>
              <Text color="gray.600" fontSize="sm">
                Admin Panel Access
              </Text>
            </VStack>

            {/* Info Alert */}
            <Alert status="info" borderRadius="md" fontSize="sm">
              <AlertIcon />
              Enter the admin password to access the management panel
            </Alert>

            {/* Login Form */}
            <form onSubmit={handleLogin} style={{ width: '100%' }}>
              <VStack spacing={4} w="full">
                <FormControl isRequired>
                  <FormLabel color="gray.700" fontSize="sm" fontWeight="medium">
                    Username
                  </FormLabel>
                  <Input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username"
                    size="lg"
                    bg="white"
                    color="black"
                    border="2px solid"
                    borderColor="gray.200"
                    _hover={{ borderColor: "blue.300" }}
                    _focus={{
                      borderColor: "blue.500",
                      boxShadow: "0 0 0 1px blue.500"
                    }}
                    disabled={isLoading}
                  />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel color="gray.700" fontSize="sm" fontWeight="medium">
                    Password
                  </FormLabel>
                  <InputGroup>
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Enter password"
                      size="lg"
                      bg="white"
                      color="black"
                      border="2px solid"
                      borderColor="gray.200"
                      _hover={{ borderColor: "blue.300" }}
                      _focus={{
                        borderColor: "blue.500",
                        boxShadow: "0 0 0 1px blue.500"
                      }}
                      disabled={isLoading}
                    />
                    <InputRightElement height="full">
                      <IconButton
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        icon={showPassword ? <ViewOffIcon /> : <ViewIcon />}
                        onClick={() => setShowPassword(!showPassword)}
                        variant="ghost"
                        size="sm"
                        color="gray.500"
                        _hover={{ color: "blue.500" }}
                        disabled={isLoading}
                      />
                    </InputRightElement>
                  </InputGroup>
                </FormControl>
                <Button
                  type="submit"
                  variant="mirando"
                  size="lg"
                  w="full"
                  isLoading={isLoading}
                  loadingText="Authenticating..."
                  disabled={!username.trim() || !password.trim()}
                  _hover={{ transform: 'translateY(-1px)' }}
                  transition="all 0.2s"
                >
                  🔐 Access Admin Panel
                </Button>
              </VStack>
            </form>

            {/* Footer Links */}
            <HStack spacing={4} fontSize="sm" color="gray.500">
              <Button
                variant="link"
                size="sm"
                color="blue.500"
                onClick={() => router.push('/')}
                disabled={isLoading}
              >
                ← Back to Camera
              </Button>
            </HStack>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
}