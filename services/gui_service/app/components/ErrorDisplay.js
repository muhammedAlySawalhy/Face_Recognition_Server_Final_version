'use client';

import { Box, VStack, Text, Heading, Button, Alert, AlertIcon } from '@chakra-ui/react';

export default function ErrorDisplay({ 
  title = "Something went wrong", 
  message = "An unexpected error occurred. Please try again.", 
  onRetry,
  showLogo = true,
  minHeight = "50vh" 
}) {
  return (
    <Box 
      bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
      minH={minHeight}
      display="flex"
      alignItems="center"
      justifyContent="center"
      py={8}
    >
      <VStack spacing={6} maxW="md" mx="auto" px={4}>
        {showLogo && (
          <VStack spacing={2}>
            <Heading 
              as="h1" 
              size="lg" 
              color="white" 
              fontWeight="bold"
              textShadow="2px 2px 4px rgba(0,0,0,0.5)"
            >
              Mirando Solutions
            </Heading>
            <Text color="blue.300" fontSize="md">
              Identity Verification System
            </Text>
          </VStack>
        )}
        
        <Alert 
          status="error" 
          variant="solid" 
          borderRadius="lg"
          bg="red.500"
          color="white"
        >
          <AlertIcon color="white" />
          <VStack spacing={2} align="start" flex={1}>
            <Text fontWeight="bold" fontSize="lg">
              {title}
            </Text>
            <Text fontSize="sm">
              {message}
            </Text>
          </VStack>
        </Alert>

        {onRetry && (
          <Button
            variant="mirando"
            onClick={onRetry}
            size="lg"
            _hover={{ transform: 'translateY(-1px)' }}
          >
            🔄 Try Again
          </Button>
        )}
      </VStack>
    </Box>
  );
}