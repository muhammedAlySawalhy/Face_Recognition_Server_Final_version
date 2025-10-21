'use client';

import {
  Box,
  Button,
  Center,
  Flex,
  Image,
  Stack,
  Text,
  useToast,
  VStack,
  HStack,
  Heading,
  Card,
  CardBody,
  Badge
} from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function ResultPhotoPage() {
  const router = useRouter();
  const [capturedPhoto, setCapturedPhoto] = useState("");
  const [capturedUsername, setCapturedUsername] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    const photo = localStorage.getItem('capturedPhoto');
    const username = localStorage.getItem('capturedUsername');
    
    if (photo && username) {
      setCapturedPhoto(photo);
      setCapturedUsername(username);
    } else {
      // Redirect to home if no captured data found
      router.push('/');
    }
  }, [router]);

  const handleRetakePhoto = () => {
    localStorage.removeItem('capturedPhoto');
    localStorage.removeItem('capturedUsername');
    router.push('/');
  };

  const handleGoToAdmin = () => {
    router.push('/admin');
  };

  const handleClearAndHome = () => {
    localStorage.removeItem('capturedPhoto');
    localStorage.removeItem('capturedUsername');
    router.push('/');
  };

  if (!capturedPhoto || !capturedUsername) {
    return (
      <Box 
        bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Text color="white" fontSize="lg">No captured photo found</Text>
          <Button colorScheme="blue" onClick={() => router.push('/')}>
            Go to Camera
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <Box 
      bg="linear-gradient(135deg, #000000 0%, #1a365d 50%, #2d3748 100%)"
      minH="100vh"
      py={6}
    >
      {/* Header */}
      <Box textAlign="center" mb={6}>
        <Heading 
          as="h1" 
          size="xl" 
          color="white" 
          fontWeight="bold"
          textShadow="2px 2px 4px rgba(0,0,0,0.5)"
        >
          Mirando Solutions
        </Heading>
        <Text color="blue.300" fontSize="lg" mt={2}>
          Photo Captured Successfully
        </Text>
      </Box>

      <Center>
        <Card 
          maxW="md" 
          variant="mirando"
          overflow="hidden"
        >
          <CardBody p={6}>
            <VStack spacing={6}>
              {/* Status Badge */}
              <Badge
                colorScheme="yellow"
                variant="solid"
                fontSize="sm"
                px={4}
                py={2}
                borderRadius="full"
              >
                PENDING APPROVAL
              </Badge>

              {/* User Photo */}
              <Box>
                <Image
                  borderRadius="full"
                  boxSize="200px"
                  src={capturedPhoto}
                  alt={`${capturedUsername} photo`}
                  objectFit="cover"
                  border="4px solid"
                  borderColor="blue.500"
                  boxShadow="lg"
                />
              </Box>

              {/* User Details */}
              <VStack spacing={2} textAlign="center">
                <Text fontSize="2xl" fontWeight="bold" color="black">
                  {capturedUsername}
                </Text>
                <Text fontSize="md" color="gray.600">
                  Photo submitted for verification
                </Text>
                <Text fontSize="sm" color="gray.500">
                  {new Date().toLocaleString()}
                </Text>
              </VStack>

              {/* Information Text */}
              <Box 
                bg="blue.50" 
                p={4} 
                borderRadius="md" 
                border="1px solid" 
                borderColor="blue.200"
                textAlign="center"
              >
                <Text fontSize="sm" color="blue.800" fontWeight="semibold">
                  ✅ Your photo has been added to the pending approval queue
                </Text>
                <Text fontSize="xs" color="blue.600" mt={2}>
                  An administrator will review and approve your submission
                </Text>
              </Box>

              {/* Action Buttons */}
              <VStack spacing={3} width="100%">
                <HStack spacing={4} width="100%">
                  <Button
                    flex={1}
                    variant="outline"
                    colorScheme="blue"
                    onClick={handleRetakePhoto}
                    size="md"
                    _hover={{ transform: 'translateY(-1px)' }}
                  >
                    📸 Retake Photo
                  </Button>
                  <Button
                    flex={1}
                    variant="mirando"
                    onClick={handleGoToAdmin}
                    size="md"
                  >
                    👥 View Admin Panel
                  </Button>
                </HStack>
                
                <Button
                  width="100%"
                  variant="mirandoSecondary"
                  onClick={handleClearAndHome}
                  size="md"
                >
                  🏠 Start New Capture
                </Button>
              </VStack>

              {/* Footer Info */}
              <Text fontSize="xs" color="gray.500" textAlign="center">
                Powered by Mirando Solutions Identity Verification System
              </Text>
            </VStack>
          </CardBody>
        </Card>
      </Center>
    </Box>
  );
}