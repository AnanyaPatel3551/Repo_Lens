'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { analyzeRepository } from '../lib/api';

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const validateUrl = (githubUrl: string): boolean => {
    const cleaned = githubUrl.trim().replace(/\/$/, '');
    const cleanUrl = cleaned.endsWith('.git') ? cleaned.slice(0, -4) : cleaned;
    
    // Pattern matches github.com/owner/repo
    const pattern = /^https?:\/\/(?:www\.)?github\.com\/[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+$/;
    return pattern.test(cleanUrl);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const targetUrl = url.trim();
    if (!targetUrl) {
      setError('Please enter a GitHub repository URL.');
      return;
    }

    if (!validateUrl(targetUrl)) {
      setError('Must be a valid public GitHub URL (e.g. https://github.com/owner/repo).');
      return;
    }

    setLoading(true);
    try {
      const response = await analyzeRepository(targetUrl);
      // Success: redirect to report page
      router.push(`/reports/${response.report_id}`);
    } catch (err: any) {
      setError(err.message || 'An error occurred while submitting the repository.');
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center relative px-4 py-16 grid-bg">
      {/* Glow ambient background effect */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none"></div>

      <div className="max-w-xl w-full text-center z-10">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 bg-clip-text text-transparent bg-gradient-to-b from-white via-zinc-100 to-zinc-500">
          Analyze Any GitHub Repository
        </h1>
        <p className="text-zinc-400 text-base sm:text-lg mb-8 max-w-lg mx-auto">
          Paste a public GitHub link. Get instantly compiled reports on files count, languages breakdown, framework checks, and entry point paths.
        </p>

        {/* Form Card */}
        <div className="bg-[#121215]/80 border border-[#27272a]/70 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-zinc-700">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="text-left space-y-1.5">
              <label htmlFor="github-url" className="text-xs font-semibold text-zinc-400 tracking-wide uppercase">
                GitHub Repository URL
              </label>
              <div className="relative rounded-lg shadow-sm">
                <input
                  type="text"
                  id="github-url"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="https://github.com/facebook/react"
                  disabled={loading}
                  className={`w-full px-4 py-3 bg-zinc-900 border ${
                    error ? 'border-red-500/70 focus:ring-red-500/30' : 'border-zinc-800 focus:ring-indigo-500/30'
                  } rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:ring-4 transition-all`}
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 text-left bg-red-500/5 border border-red-500/20 px-3.5 py-2.5 rounded-lg">
                <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:bg-zinc-800 disabled:text-zinc-500 disabled:border-zinc-700/50 border border-transparent transition-all shadow-lg hover:shadow-indigo-500/10"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-zinc-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Initializing Analysis...
                </>
              ) : (
                <>
                  Analyze Repository
                  <svg className="w-4.5 h-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature quick badges */}
        <div className="mt-10 flex flex-wrap justify-center gap-6 text-zinc-500 text-xs font-medium uppercase tracking-wider">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
            8 Languages
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
            8 Frameworks
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
            Dependency Parser
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
            Entry Point Map
          </div>
        </div>
      </div>
    </div>
  );
}
