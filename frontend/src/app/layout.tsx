import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Newtonite Operations Dashboard",
  description: "Enterprise Operations Management Platform MVP",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 min-h-screen antialiased selection:bg-indigo-500 selection:text-white`}>
        <AuthProvider>
          <div className="min-h-screen flex flex-col">
            <Suspense fallback={<div className="h-16 border-b border-slate-800 bg-slate-950/80" />}>
              <Navbar />
            </Suspense>
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <Suspense fallback={<div className="py-20 text-center text-slate-400">Loading...</div>}>
                {children}
              </Suspense>
            </main>
            <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
              Newtonite Operations Management System &bull; Enterprise Reliability Assessment MVP
            </footer>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
