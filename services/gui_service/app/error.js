'use client';

import { useEffect } from 'react';
import { Box, VStack, Heading, Text, Button } from '@chakra-ui/react';

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error('Global error:', error);
  }, [error]);

  return (
    <Box 
      bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      py={8}
    >
      <VStack spacing={8} textAlign="center" maxW="md" mx="auto" px={4}>
        {/* Logo */}
        <VStack spacing={2}>
          <Heading 
            as="h1" 
            size="xl" 
            color="white" 
            fontWeight="bold"
            textShadow="2px 2px 4px rgba(0,0,0,0.5)"
          >
            Mirando Solutions
          </Heading>
          <Text color="blue.300" fontSize="lg">
            Identity Verification System
          </Text>
        </VStack>

        {/* Error Message */}
        <VStack spacing={4}>
          <Text 
            fontSize="6xl" 
            color="red.400"
            lineHeight="1"
          >
            ⚠️
          </Text>
          
          <Heading 
            as="h2" 
            size="lg" 
            color="white"
            fontWeight="semibold"
          >
            Something went wrong
          </Heading>
          
          <Text 
            color="gray.300" 
            fontSize="md"
            textAlign="center"
            maxW="sm"
          >
            An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
          </Text>

          {process.env.NODE_ENV === 'development' && (
            <Box 
              bg="red.900" 
              color="red.100" 
              p={4} 
              borderRadius="md" 
              fontSize="sm"
              fontFamily="mono"
              maxW="full"
              overflow="auto"
            >
              <Text fontWeight="bold" mb={2}>Error Details:</Text>
              <Text>{error?.message || 'Unknown error'}</Text>
            </Box>
          )}
        </VStack>

        {/* Action Buttons */}
        <VStack spacing={4} width="100%">
          <Button
            variant="mirando"
            size="lg"
            onClick={reset}
            width="250px"
            _hover={{ transform: 'translateY(-2px)' }}
          >
            🔄 Try Again
          </Button>
          
          <Button
            variant="outline"
            colorScheme="blue"
            color="white"
            borderColor="mirando.blue"
            size="lg"
            onClick={() => window.location.href = '/'}
            width="250px"
            _hover={{ 
              bg: "mirando.blue", 
              borderColor: "mirando.blue",
              transform: 'translateY(-2px)'
            }}
          >
            🏠 Go Home
          </Button>
        </VStack>

        {/* Footer */}
        <Text fontSize="sm" color="gray.500" textAlign="center">
          If this error persists, please contact Mirando Solutions support
        </Text>
      </VStack>
    </Box>
  );
}