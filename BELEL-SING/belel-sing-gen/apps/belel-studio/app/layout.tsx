import "@/styles/globals.css";
import React from "react";
import { Providers } from "@/components/shell/Providers";
import { AppShell } from "@/components/shell/AppShell";

export const metadata = {
  title: "Belel Studio",
  description: "Belel Studio UI v1"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}