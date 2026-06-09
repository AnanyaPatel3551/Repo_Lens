import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RepoLens AI | Repository Intelligence",
  description: "Get clean and fast production-ready repo scanning, framework matching, language details, and entry points detection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-[#0a0a0c] text-[#f4f4f5] flex flex-col antialiased selection:bg-indigo-500/30">
        <header className="border-b border-[#27272a]/60 bg-[#0a0a0c]/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              {/* Sleek SVG Logo */}
              <svg className="w-6 h-6 text-indigo-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                <line x1="12" y1="22.08" x2="12" y2="12" />
              </svg>
              <a href="/" className="font-semibold text-lg tracking-tight hover:text-indigo-400 transition-colors">
                RepoLens <span className="text-indigo-500">AI</span>
              </a>
            </div>
            <div className="flex items-center gap-4">
              <a 
                href="https://github.com" 
                target="_blank" 
                rel="noreferrer"
                className="text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                GitHub Docs
              </a>
              <span className="text-zinc-700">|</span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700/50">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                v1.0.0
              </span>
            </div>
          </div>
        </header>
        <main className="flex-1 flex flex-col">
          {children}
        </main>
        <footer className="border-t border-[#27272a]/40 bg-[#070709] py-8 text-center text-xs text-zinc-500">
          <div className="max-w-7xl mx-auto px-4">
            <p>© {new Date().getFullYear()} RepoLens AI. Built for production repository metrics & intelligence.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
