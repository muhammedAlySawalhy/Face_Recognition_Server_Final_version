"use client"
console.log("[DEBUG] ClientProvider file loaded");


import { ChakraProvider, extendTheme } from '@chakra-ui/react';
import { AuthProvider } from './contexts/AuthContext';
import { useEffect } from 'react';
import { DashboardProvider } from './DashboardContext';

// Mirando Solutions theme with black and blue colors
const theme = extendTheme({
  colors: {
    brand: {
      50: '#e6f3ff',
      100: '#b3d9ff',
      200: '#80bfff',
      300: '#4da6ff',
      400: '#1a8cff',
      500: '#0073e6',
      600: '#005bb3',
      700: '#004280',
      800: '#00294d',
      900: '#00101a',
    },
    mirando: {
      black: '#000000',
      blue: '#0073e6',
      darkBlue: '#005bb3',
      lightBlue: '#4da6ff',
    },
    gray: {
      900: '#181A20',
      800: '#232946',
      700: '#2d3748',
      600: '#4a5568',
      500: '#718096',
      400: '#a0aec0',
      300: '#cbd5e0',
      200: '#e2e8f0',
      100: '#f7fafc',
    },
  },
  fonts: {
    heading: 'Inter, system-ui, sans-serif',
    body: 'Inter, system-ui, sans-serif',
  },
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  styles: {
    global: {
      body: {
        bg: 'linear-gradient(135deg, #0a0a23 0%, #1a365d 50%, #232946 100%)',
        color: 'white',
      },
    },
  },
  components: {
    Button: {
      variants: {
        mirando: {
          bg: 'mirando.blue',
          color: 'white',
          _hover: {
            bg: 'mirando.darkBlue',
            transform: 'translateY(-1px)',
          },
          _active: {
            transform: 'translateY(0)',
          },
        },
        mirandoSecondary: {
          bg: 'mirando.black',
          color: 'white',
          _hover: {
            bg: 'gray.800',
            transform: 'translateY(-1px)',
          },
          _active: {
            transform: 'translateY(0)',
          },
        },
      },
    },
    Card: {
      variants: {
        mirando: {
          container: {
            bg: 'gray.900',
            border: '2px solid',
            borderColor: 'mirando.blue',
            borderRadius: 'xl',
            boxShadow: '2xl',
          },
        },
      },
    },
  },
});

export default function ClientProvider({ children }) {
  
  useEffect(() => {
    console.log("[DEBUG] ClientProvider mounted");
  }, []);
  return (
    <AuthProvider>
      <ChakraProvider theme={theme}>
        <DashboardProvider>

        {children}
        </DashboardProvider>
      </ChakraProvider>
    </AuthProvider>
  );
}