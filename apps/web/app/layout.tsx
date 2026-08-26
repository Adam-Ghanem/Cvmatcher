import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CVMatcher | Career intelligence",
    template: "%s | CVMatcher",
  },
  description:
    "CVMatcher turns your CV and target role into transparent career intelligence and practical next steps.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
