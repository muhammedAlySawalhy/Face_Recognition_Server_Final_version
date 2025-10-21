

import "../styles/globals.css";
import ClientRoot from "./client-root";
import EnvVariablesScript from "./components/EnvVariablesScript";

export const metadata = {
  title: "Mirando Solutions - Identity Verification System",
  description:
    "Professional identity verification and user management system powered by Mirando Solutions",
  keywords:
    "identity verification, user management, camera capture, Mirando Solutions",
  viewport: "width=device-width, initial-scale=1",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <EnvVariablesScript />
      </head>
      <body>
        <ClientRoot>{children}</ClientRoot>
      </body>
    </html>
  );
}
