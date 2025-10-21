'use client';

import { Box, VStack, Spinner, Text, Heading } from '@chakra-ui/react';

export default function Loading({ 
  message = "Loading...", 
  size = "xl", 
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
      <VStack spacing={6}>
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
        
        <VStack spacing={4}>
          <Spinner 
            size={size} 
            color="mirando.blue" 
            thickness="4px"
            speed="0.65s"
          />
          <Text 
            color="white" 
            fontSize="lg"
            textAlign="center"
          >
            {message}
          </Text>
        </VStack>
      </VStack>
    </Box>
  );
}