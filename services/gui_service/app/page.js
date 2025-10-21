'use client';

import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Button,
  Center,
  Flex,
  useMediaQuery,
  Input,
  VStack,
  Text,
  useToast,
  FormControl,
  FormLabel,
  HStack,
  Heading,
  Image
} from "@chakra-ui/react";
import { Camera } from "react-camera-pro";
import { FiCamera } from "react-icons/fi";
import { useRouter } from "next/navigation";
import { CheckCircleIcon } from "@chakra-ui/icons"; // Add this import
import Permission from "./components/Permission";
import { useAuth } from "./contexts/AuthContext";
import { useDashboard, useUserLookup } from "./DashboardContext";

export default function HomePage() {
  const router = useRouter();
  const { hasPermission, refreshUser, isAuthenticated, isLoading: authLoading } = useAuth();
  const { findUserByNationalIdExcel } = useUserLookup();

  const camera = useRef(null);
  const [numberOfCameras, setNumberOfCameras] = useState(0);
  const [image, setImage] = useState(null);
  const [nationalId, setNationalId] = useState("");
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [mobileScreen] = useMediaQuery('(min-width: 600px)');
  const [ratio, setRatio] = useState(9 / 16);
  const [previewMode, setPreviewMode] = useState(false);
  const toast = useToast();

  // Function to lookup user by National ID
  const handleNationalIdChange = (value) => {
    setNationalId(value);
    setUserInfo(null); // Clear previous user info

    if (value.trim().length >= 3) { // Start lookup when at least 3 characters entered
      setLookupLoading(true);
      // Debounce the lookup
      setTimeout(async () => {
        const foundUser = await findUserByNationalIdExcel(value.trim());
        console.log('Found user:', foundUser);
        setUserInfo(foundUser);
        setLookupLoading(false);
      }, 500);
    }
  };
  // Check authentication and redirect if not authenticated
  useEffect(() => {
    refreshUser();
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      toast({
        title: "Authentication Required",
        description: "Please log in to access the camera.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      router.push('/admin/login');
    }
  }, [authLoading, isAuthenticated, router, toast]);

  useEffect(() => {
    // Set camera ratio based on screen size
    if (mobileScreen) {
      setRatio(9 / 16);
    } else {
      setRatio("cover");
    }
  }, [mobileScreen]);

  const rotateImage = (imageBase64, rotation) => {
    return new Promise((resolve) => {
      const img = new window.Image();
      img.src = imageBase64;
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext("2d");
        ctx.translate(canvas.width, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(img, 0, 0);
        resolve(canvas.toDataURL("image/jpeg"));
      };
    });
  };

  const addUserToPending = async (imageData) => {
    try {
      // Find user info from Excel data
      const foundUser = await findUserByNationalIdExcel(nationalId);

      if (!foundUser) {
        toast({
          title: "User Not Found",
          description: `No user found with National ID: ${nationalId}`,
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        return;
      }

      // Use the user's username from Excel data for the API call
      const response = await fetch('/api/users/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: foundUser.username,
          nationalId: nationalId,
          userInfo: foundUser,
          imageData,
          action: 'pending'
        }),
      });

      const result = await response.json();

      if (result.success) {
        toast({
          title: "Success!",
          description: `User ${foundUser.name} (${foundUser.username}) added to pending approval`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });

        // Reset form
        setNationalId("");
        setUserInfo(null);
        setImage(null);

        // Redirect to admin panel after a delay
        // setTimeout(() => {
        //   router.push("/admin");
        // }, 2000);
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Error adding user:', error);
      toast({
        title: "Error",
        description: "Failed to add user. Please try again.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleCapture = async () => {
    // Check if user has camera permission
    if (!hasPermission("capture_photo")) {
      toast({
        title: "Permission Denied",
        description: "You don't have permission to capture photos. Please contact an administrator.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    if (!nationalId.trim()) {
      toast({
        title: "National ID Required",
        description: "Please enter a National ID before taking a photo",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Find user by National ID
    const foundUser = await findUserByNationalIdExcel(nationalId);
    if (!foundUser) {
      toast({
        title: "User Not Found",
        description: `No user found with National ID: ${nationalId}. Please check the ID and try again.`,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setUserInfo(foundUser);

    setIsLoading(true);
    try {
      if (!camera.current || typeof camera.current.takePhoto !== 'function') {
        toast({
          title: "Camera Error",
          description: "Camera is not ready. Please refresh the page or check your device.",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      const imageSrc = camera.current.takePhoto();
      console.log('Camera imageSrc:', imageSrc);
      if (!imageSrc) {
        toast({
          title: "Capture Error",
          description: "Failed to capture photo. Please ensure your camera is working and try again.",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      const rotatedImage = await rotateImage(imageSrc, 90);
      setImage(rotatedImage);
      setPreviewMode(true); // Enable preview mode
    } catch (error) {
      console.error('Error capturing photo:', error);
      toast({
        title: "Capture Error",
        description: "Failed to capture photo. Please try again.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      // Store in localStorage for preview
      localStorage.setItem('capturedPhoto', image);
      localStorage.setItem('capturedNationalId', nationalId);
      localStorage.setItem('capturedUserInfo', JSON.stringify(userInfo));

      // Add to pending
      await addUserToPending(image);

    } catch (error) {
      console.error('Error confirming photo:', error);
      toast({
        title: "Submission Error",
        description: "Failed to submit photo. Please try again.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
      setPreviewMode(false);
    }
  };

  const handleClear = () => {
    setNationalId("");
    setUserInfo(null);
    setImage(null);
    setPreviewMode(false);
    setLookupLoading(false);
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <Box
        bg="#101114"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Box className="spinner" width="60px" height="60px" />
          <Text color="#e0eaff" fontSize="lg">
            Checking authentication...
          </Text>
        </VStack>
      </Box>
    );
  }

  // Don't render camera if not authenticated (redirect will happen via useEffect)
  if (!isAuthenticated) {
    return (
      <Box
        bg="#101114"
        minH="100vh"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing={4}>
          <Text color="#e0eaff" fontSize="lg">
            Redirecting to login...
          </Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box
      bg="#101114"
      minH="100vh"
      py={4}
    >
      {/* Header */}
      <Box textAlign="center" mb={6}>
        <Image
          src="/112.png"
          alt="Mirando Solutions Logo"
          boxSize={{ base: "100px", md: "120px" }}
          objectFit="contain"
          mx="auto"
          mb={2}
        />
        <Heading
          as="h1"
          size="2xl"
          color="#e0eaff"
          fontWeight="extrabold"
          letterSpacing="wide"
          textShadow="0 4px 24px #000a, 0 1px 0 #1a365d"
        >
          Mirando Solutions
        </Heading>
        <Text color="#7ecbff" fontSize="xl" mt={2} fontWeight="semibold" letterSpacing="wider">
          Identity Verification System
        </Text>
      </Box>

      <Center>
        <Box
          maxW="lg"
          width={{ base: '95%', md: '600px', lg: '500px' }}
          bg="whiteAlpha.900"
          borderRadius="2xl"
          boxShadow="2xl"
          overflow="hidden"
          border="2px solid"
          borderColor="blue.400"
        >
          {/* Form Section */}
          <Box p={6} bg="gray.50" borderBottom="1px solid" borderColor="gray.200">
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel color="black" fontWeight="semibold">
                  National ID
                </FormLabel>
                <Input
                  color={"black"}
                  placeholder="Enter National ID"
                  value={nationalId}
                  onChange={(e) => handleNationalIdChange(e.target.value)}
                  bg="white"
                  borderColor="blue.300"
                  _hover={{ borderColor: "blue.400" }}
                  _focus={{ borderColor: "blue.500", boxShadow: "0 0 0 1px #3182ce" }}
                />
              </FormControl>

              {/* Loading state for lookup */}
              {lookupLoading && (
                <Box
                  p={3}
                  bg="blue.50"
                  borderRadius="md"
                  border="1px solid"
                  borderColor="blue.200"
                  width="100%"
                >
                  <Text fontSize="sm" color="blue.600">
                    Looking up user...
                  </Text>
                </Box>
              )}

              {/* Show user info when found */}
              {userInfo && !lookupLoading && (
                <Box
                  p={4}
                  bg="green.50"
                  borderRadius="md"
                  border="1px solid"
                  borderColor="green.200"
                  width="100%"
                >
                  <VStack spacing={2} align="start">
                    <Text fontSize="sm" fontWeight="bold" color="green.800">
                      User Found:
                    </Text>
                    <Text fontSize="sm" color="gray.700">
                      <strong>Name:</strong> {userInfo.name}
                    </Text>
                    <Text fontSize="sm" color="gray.700">
                      <strong>Username:</strong> {userInfo.username}
                    </Text>
                    <Text fontSize="sm" color="gray.700">
                      <strong>Department:</strong> {userInfo.department}
                    </Text>
                    <Text fontSize="sm" color="gray.700">
                      <strong>Government:</strong> {userInfo.government}
                    </Text>
                    <Text fontSize="sm" color="gray.700">
                      <strong>national ID:</strong> {userInfo.nationalId}
                    </Text>
                  </VStack>
                </Box>
              )}

              {/* Show message when not found */}
              {nationalId.trim().length >= 3 && !userInfo && !lookupLoading && (
                <Box
                  p={3}
                  bg="red.50"
                  borderRadius="md"
                  border="1px solid"
                  borderColor="red.200"
                  width="100%"
                >
                  <Text fontSize="sm" color="red.600">
                    No user found with this National ID
                  </Text>
                </Box>
              )}
            </VStack>
          </Box>

          {/* Preview Section */}
          {previewMode && (
            <Box p={4} bg="blue.50" borderBottom="1px solid" borderColor="blue.200">
              <VStack spacing={3}>
                <Text fontWeight="bold" color="blue.800">Preview</Text>

                {/* User Info Display */}
                {userInfo && (
                  <Box
                    p={3}
                    bg="white"
                    borderRadius="md"
                    border="1px solid"
                    borderColor="blue.200"
                    width="100%"
                  >
                    <VStack spacing={1} align="start">
                      <Text fontSize="sm" color="gray.700">
                        <strong>National ID:</strong> {nationalId}
                      </Text>
                      <Text fontSize="sm" color="gray.700">
                        <strong>Name:</strong> {userInfo.name}
                      </Text>
                      <Text fontSize="sm" color="gray.700">
                        <strong>Username:</strong> {userInfo.username}
                      </Text>
                      <Text fontSize="sm" color="gray.700">
                        <strong>Department:</strong> {userInfo.department}
                      </Text>
                      <Text fontSize="sm" color="gray.700">
                        <strong>Government:</strong> {userInfo.government}
                      </Text>
                    </VStack>
                  </Box>
                )}

                {image && (
                  <Box boxShadow="md" borderRadius="md" overflow="hidden">
                    <img src={image} alt="Preview" style={{ width: "200px", borderRadius: "8px" }} />
                  </Box>
                )}
                <HStack>
                  <Button
                    leftIcon={<CheckCircleIcon />}
                    colorScheme="green"
                    onClick={handleConfirm}
                    isLoading={isLoading}
                  >
                    Confirm & Submit
                  </Button>
                  <Button
                    variant="outline"
                    colorScheme="red"
                    onClick={handleClear}
                    disabled={isLoading}
                  >
                    Retake
                  </Button>
                </HStack>
              </VStack>
            </Box>
          )}

          {/* Camera Section */}
          <Permission permission="capture_photo">
            {!previewMode && (
              <Box position="relative" bg="black">
                <Center>
                  <Box
                    position="relative"
                    width="100%"
                    height={{ base: "400px", md: "450px" }}
                    overflow="hidden"
                  >
                    <Camera
                      ref={camera}
                      numberOfCamerasCallback={setNumberOfCameras}
                      facingMode="user"
                      aspectRatio={ratio}
                      style={{ width: '100%', height: '100%' }}
                    />

                    {/* Official Capture Button */}
                    <Button
                      leftIcon={<FiCamera size={22} />}
                      position="absolute"
                      bottom="20px"
                      left="50%"
                      transform="translateX(-50%)"
                      onClick={handleCapture}
                      isLoading={isLoading}
                      loadingText="Capturing..."
                      colorScheme="blue"
                      size="lg"
                      borderRadius="full"
                      width="200px"
                      height="60px"
                      fontWeight="bold"
                      fontSize="lg"
                      _hover={{
                        transform: "translateX(-50%) scale(1.05)",
                        bg: "blue.500",
                        color: "white"
                      }}
                      _active={{ transform: "translateX(-50%) scale(0.95)" }}
                      transition="all 0.2s"
                      boxShadow="lg"
                      border="2px solid white"
                      disabled={!nationalId.trim() || isLoading || !hasPermission("capture_photo")}
                    >
                      Capture Photo
                    </Button>

                    {/* Camera overlay for better UX */}
                    <Box
                      position="absolute"
                      top="20px"
                      left="20px"
                      right="20px"
                      zIndex={2}
                    >
                      <Text
                        color="white"
                        fontSize="sm"
                        textAlign="center"
                        bg="rgba(0,0,0,0.6)"
                        borderRadius="md"
                        p={2}
                      >
                        Position yourself in the frame
                      </Text>
                    </Box>
                  </Box>
                </Center>
              </Box>
            )}
          </Permission>

          {/* No Camera Permission Message
          <Permission permission="capture_photo" fallback>
            <Box p={6} bg="red.50" borderColor="red.200" border="1px solid">
              <VStack spacing={3}>
                <Text color="red.600" fontWeight="bold" fontSize="lg">
                  Camera Access Restricted
                </Text>
                <Text color="red.500" textAlign="center">
                  You don't have permission to access the camera. Please contact an administrator to request camera access permissions.
                </Text>
              </VStack>
            </Box>
          </Permission> */}

          {/* Action Buttons */}
          <Box p={6} bg="gray.50">
            <VStack spacing={3}>
              <HStack spacing={4} width="100%">
                <Button
                  flex={1}
                  variant="outline"
                  colorScheme="blue"
                  onClick={() => router.push("/admin")}
                >
                  View Admin Panel
                </Button>
                <Button
                  flex={1}
                  variant="mirandoSecondary"
                  onClick={handleClear}
                  disabled={isLoading}
                >
                  Clear Form
                </Button>
              </HStack>

              <Text fontSize="xs" color="gray.600" textAlign="center">
                Your photo will be added to pending approval queue
              </Text>
            </VStack>
          </Box>
        </Box>
      </Center>
    </Box>
  );
}