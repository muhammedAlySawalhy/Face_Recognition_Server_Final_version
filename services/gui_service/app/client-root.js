"use client";
import ClientProvider from "./Providers";
import { RuntimeEnvProvider } from "./contexts/RuntimeEnvContext";

export default function ClientRoot({ children }) {
  return (
    <RuntimeEnvProvider>
      <ClientProvider>{children}</ClientProvider>
    </RuntimeEnvProvider>
  );
}