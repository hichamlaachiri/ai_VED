import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "MicroDrama AI Studio | 60s Vertical Micro-Drama SaaS",
  description: "Turn story premises into consistent, ready-to-post 60s vertical AI micro-drama episodes using Gemini Omni 1.2 Flash and FFmpeg auto-assembly.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#08090E] text-slate-100 antialiased selection:bg-amber-500/30 selection:text-amber-200">
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </main>
          <footer className="border-t border-slate-800/80 bg-[#0B0D14] py-4 text-center text-xs text-slate-500">
            MicroDrama AI Studio &copy; 2026 &bull; Powered by Gemini Omni 1.2 Flash &bull; 9:16 Cinematic Pipeline
          </footer>
        </div>
      </body>
    </html>
  );
}
