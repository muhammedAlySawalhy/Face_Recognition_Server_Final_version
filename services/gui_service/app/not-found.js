'use client';

import { Box, VStack, Heading, Text, Button } from '@chakra-ui/react';
import { useRouter } from 'next/navigation';

export default function NotFound() {
  const router = useRouter();

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

        {/* 404 Error */}
        <VStack spacing={4}>
          <Text 
            fontSize="8xl" 
            fontWeight="bold" 
            color="mirando.blue"
            lineHeight="1"
            textShadow="2px 2px 4px rgba(0,0,0,0.3)"
          >
            404
          </Text>
          
          <Heading 
            as="h2" 
            size="lg" 
            color="white"
            fontWeight="semibold"
          >
            Page Not Found
          </Heading>
          
          <Text 
            color="gray.300" 
            fontSize="lg"
            textAlign="center"
            maxW="sm"
          >
            The page you're looking for doesn't exist or has been moved.
          </Text>
        </VStack>

        {/* Action Buttons */}
        <VStack spacing={4} width="100%">
          <Button
            variant="mirando"
            size="lg"
            onClick={() => router.push('/')}
            width="250px"
            _hover={{ transform: 'translateY(-2px)' }}
          >
            📸 Go to Camera
          </Button>
          
          <Button
            variant="outline"
            colorScheme="blue"
            color="white"
            borderColor="mirando.blue"
            size="lg"
            onClick={() => router.push('/admin')}
            width="250px"
            _hover={{ 
              bg: "mirando.blue", 
              borderColor: "mirando.blue",
              transform: 'translateY(-2px)'
            }}
          >
            👥 Admin Panel
          </Button>
        </VStack>

        {/* Footer */}
        <Text fontSize="sm" color="gray.500" textAlign="center">
          © 2024 Mirando Solutions. All rights reserved.
        </Text>
      </VStack>
    </Box>
  );
}