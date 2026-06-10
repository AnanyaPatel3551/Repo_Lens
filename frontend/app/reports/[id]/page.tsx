'use client';

import React, { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { getReport, askQuestion, getTour, getWalkthrough, getFileContent, getGraph, getExplanation, getDiagrams } from '../../../lib/api';
import { AnalysisReport, DependencyItem, Citation, TourStep } from '../../../types';

// Language Color Mapping
const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3572A5',
  JavaScript: '#F1E05A',
  TypeScript: '#3178C6',
  Java: '#B07219',
  Go: '#00ADD8',
  Rust: '#DEA584',
  'C++': '#F34B7D',
  'C#': '#178600',
};

const DEFAULT_LANG_COLOR = '#71717a';

function MermaidRenderer({ chart }: { chart: string }) {
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    try {
      const cleaned = chart.trim();
      const encoded = btoa(unescape(encodeURIComponent(cleaned)));
      setImgUrl(`https://mermaid.ink/svg/${encoded}`);
      setError(false);
    } catch (err) {
      setError(true);
    }
  }, [chart]);

  if (error) {
    return (
      <pre className="bg-[#0a0a0c] p-4 rounded-xl border border-zinc-800 text-[10px] text-zinc-400 font-mono whitespace-pre overflow-auto max-h-[350px]">
        {chart}
      </pre>
    );
  }

  return (
    <div className="w-full flex justify-center bg-[#0a0a0c] p-4 rounded-xl border border-zinc-800/80 overflow-auto">
      {imgUrl ? (
        <img
          src={imgUrl}
          alt="Architecture Flowchart"
          className="max-w-full h-auto object-contain invert brightness-95"
          onError={() => setError(true)}
        />
      ) : (
        <p className="text-xs text-zinc-500 animate-pulse">Rendering diagram...</p>
      )}
    </div>
  );
}

/**
 * Safely converts any value to a renderable string.
 * Handles cases where LLM returns objects like {name, description} instead of plain strings.
 */
function toStr(val: unknown): string {
  if (typeof val === 'string') return val;
  if (val == null) return '';
  if (typeof val === 'object') {
    const obj = val as Record<string, unknown>;
    // Common LLM patterns: {name, description}, {title, content}, {text}
    if (typeof obj.name === 'string' && typeof obj.description === 'string') {
      return `${obj.name}: ${obj.description}`;
    }
    if (typeof obj.name === 'string') return obj.name;
    if (typeof obj.title === 'string') return obj.title;
    if (typeof obj.text === 'string') return obj.text;
    if (typeof obj.description === 'string') return obj.description;
    return JSON.stringify(obj);
  }
  return String(val);
}

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const { id } = use(params);
  
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'founder_demo' | 'overview' | 'architecture' | 'files' | 'onboarding' | 'ask' | 'tour' | 'walkthrough'>('founder_demo');
  const [showDeps, setShowDeps] = useState(false);

  // New states for Founder Demo Mode
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [loadingGraph, setLoadingGraph] = useState(false);
  
  const [diagrams, setDiagrams] = useState<{ request_flow: string; service_interaction: string; folder_relationship: string } | null>(null);
  const [loadingDiagrams, setLoadingDiagrams] = useState(false);
  const [activeDiagramTab, setActiveDiagramTab] = useState<'request' | 'service' | 'folder'>('request');

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeExplanation, setNodeExplanation] = useState<any | null>(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  // Platform Intelligence states
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<{ sender: 'user' | 'assistant'; text: string; citations?: Citation[] }[]>([]);
  const [asking, setAsking] = useState(false);
  
  const [tourSteps, setTourSteps] = useState<TourStep[]>([]);
  const [loadingTour, setLoadingTour] = useState(false);
  
  const [walkthroughMd, setWalkthroughMd] = useState('');
  const [loadingWalkthrough, setLoadingWalkthrough] = useState(false);
  
  const [fileViewerData, setFileViewerData] = useState<{ file_path: string; content: string; lines: string[] } | null>(null);
  const [selectedLineRange, setSelectedLineRange] = useState<[number, number] | null>(null);

  const handleCitationClick = async (filePath: string, startLine: number, endLine: number) => {
    try {
      const data = await getFileContent(id, filePath);
      setFileViewerData(data);
      setSelectedLineRange([startLine, endLine]);
    } catch (err: any) {
      alert(`Failed to load file content: ${err.message}`);
    }
  };

  const handleAskSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || asking) return;

    const query = chatInput;
    setChatInput('');
    setChatHistory((prev) => [...prev, { sender: 'user', text: query }]);
    setAsking(true);

    try {
      const res = await askQuestion(id, query);
      setChatHistory((prev) => [
        ...prev,
        { sender: 'assistant', text: res.answer, citations: res.citations }
      ]);
    } catch (err: any) {
      setChatHistory((prev) => [
        ...prev,
        { sender: 'assistant', text: `Failed to retrieve answer: ${err.message}` }
      ]);
    } finally {
      setAsking(false);
    }
  };

  const loadTour = async () => {
    if (tourSteps.length > 0 || loadingTour) return;
    setLoadingTour(true);
    try {
      const data = await getTour(id);
      setTourSteps(data.tour_steps);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingTour(false);
    }
  };

  const loadWalkthrough = async () => {
    if (walkthroughMd || loadingWalkthrough) return;
    setLoadingWalkthrough(true);
    try {
      const data = await getWalkthrough(id);
      setWalkthroughMd(data.walkthrough);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingWalkthrough(false);
    }
  };

  const loadGraph = async () => {
    setLoadingGraph(true);
    try {
      const data = await getGraph(id);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoadingGraph(false);
    }
  };

  const loadDiagrams = async () => {
    setLoadingDiagrams(true);
    try {
      const data = await getDiagrams(id);
      setDiagrams(data);
    } catch (err) {
      console.error('Failed to load diagrams:', err);
    } finally {
      setLoadingDiagrams(false);
    }
  };

  const handleNodeClick = async (nodeId: string, nodeType: string) => {
    setSelectedNodeId(nodeId);
    setLoadingExplanation(true);
    setNodeExplanation(null);
    try {
      const res = await getExplanation(id, nodeId, 'file');
      setNodeExplanation(res);
    } catch (err) {
      console.error('Failed to load node explanation:', err);
    } finally {
      setLoadingExplanation(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'tour') {
      loadTour();
    } else if (activeTab === 'walkthrough') {
      loadWalkthrough();
    } else if (activeTab === 'founder_demo') {
      if (report?.status === 'completed') {
        if (!graphData) loadGraph();
        
        const loadDemoDataSequentially = async () => {
          let loadedDiagrams = diagrams;
          if (!loadedDiagrams) {
            setLoadingDiagrams(true);
            try {
              loadedDiagrams = await getDiagrams(id);
              setDiagrams(loadedDiagrams);
            } catch (err) {
              console.error('Failed to load diagrams:', err);
            } finally {
              setLoadingDiagrams(false);
            }
          }
          
          // Load tour steps sequentially after diagrams are loaded to prevent rate limiting
          if (tourSteps.length === 0) {
            setLoadingTour(true);
            try {
              const data = await getTour(id);
              setTourSteps(data.tour_steps);
            } catch (err) {
              console.error('Failed to load sequential tour:', err);
            } finally {
              setLoadingTour(false);
            }
          }
        };
        loadDemoDataSequentially();
      }
    }
  }, [activeTab, report?.status, diagrams, tourSteps.length, graphData]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const fetchStatus = async () => {
      try {
        const data = await getReport(id);
        setReport(data);
        setLoading(false);

        // Stop polling if the status is final (completed or failed)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(intervalId);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to retrieve analysis report.');
        setLoading(false);
        clearInterval(intervalId);
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 1.5 seconds while status is in-flight
    intervalId = setInterval(fetchStatus, 1500);

    return () => clearInterval(intervalId);
  }, [id]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#0a0a0c] grid-bg">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <svg className="animate-spin h-10 w-10 text-indigo-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <h2 className="text-lg font-medium text-white">Contacting Analyzer...</h2>
          <p className="text-zinc-500 text-sm">Securing communication locks with RepoLens host.</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#0a0a0c]">
        <div className="max-w-md w-full bg-[#121215] border border-red-500/20 rounded-2xl p-8 text-center shadow-xl">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4 border border-red-500/20">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Analysis Failed</h2>
          <p className="text-zinc-400 text-sm mb-6 break-words">
            {error || report?.error_message || 'An unexpected server error occurred during scan orchestration.'}
          </p>
          <button
            onClick={() => router.push('/')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-zinc-800 text-white font-medium hover:bg-zinc-700 active:bg-zinc-900 border border-zinc-700/50 transition-all text-sm"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Handle in-progress status screens (pending, cloning, analyzing)
  if (report.status !== 'completed' && report.status !== 'failed') {
    const steps = [
      { key: 'pending', label: 'Queued', desc: 'Analysis request received and scheduled.' },
      { key: 'cloning', label: 'Cloning Repository', desc: 'Downloading repository from GitHub into secure sandbox.' },
      { key: 'analyzing', label: 'Analyzing Codebase', desc: 'Running framework checks, scanners, and dependency extraction.' },
    ];
    const currentStepIndex = steps.findIndex((step) => step.key === report.status);

    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 bg-[#0a0a0c] grid-bg">
        <div className="max-w-md w-full bg-[#121215]/80 border border-[#27272a] rounded-2xl p-8 shadow-2xl backdrop-blur-xl relative">
          <div className="absolute top-0 left-0 right-0 h-1 bg-zinc-800 rounded-t-2xl overflow-hidden">
            <div 
              className="h-full bg-indigo-500 transition-all duration-500 ease-out"
              style={{ width: `${((currentStepIndex + 1) / steps.length) * 100}%` }}
            ></div>
          </div>
          
          <h2 className="text-xl font-bold text-white mb-1">Analyzing Repository</h2>
          <p className="text-zinc-400 text-xs truncate mb-6">{report.github_url}</p>

          <div className="space-y-6">
            {steps.map((step, idx) => {
              const isCompleted = idx < currentStepIndex;
              const isActive = idx === currentStepIndex;
              
              return (
                <div key={step.key} className="flex gap-4 items-start">
                  <div className="mt-1">
                    {isCompleted ? (
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center">
                        <svg className="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      </div>
                    ) : isActive ? (
                      <div className="w-5 h-5 rounded-full bg-indigo-500/10 border border-indigo-500 flex items-center justify-center animate-pulse">
                        <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                        <span className="text-[10px] font-semibold text-zinc-600">{idx + 1}</span>
                      </div>
                    )}
                  </div>
                  <div>
                    <h3 className={`text-sm font-semibold ${isActive ? 'text-white' : isCompleted ? 'text-zinc-300' : 'text-zinc-600'}`}>
                      {step.label}
                    </h3>
                    <p className={`text-xs mt-0.5 ${isActive ? 'text-zinc-400' : 'text-zinc-600'}`}>
                      {step.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Active metrics calculations
  const totalFiles = report.metrics?.total_files || 0;
  const totalLines = report.metrics?.total_lines || 0;
  const languagesList = Object.entries(report.languages || {});

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col gap-6 relative">
      
      {/* Overview Top bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#121215] border border-[#27272a] rounded-2xl p-6 shadow-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white">
              {report.repo_owner}/{report.repo_name}
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/25">
              Completed
            </span>
          </div>
          <a 
            href={report.github_url} 
            target="_blank" 
            rel="noreferrer"
            className="text-xs text-zinc-400 hover:text-indigo-400 flex items-center gap-1 transition-colors"
          >
            {report.github_url}
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => setShowDeps(!showDeps)}
            className="flex-1 sm:flex-initial px-4 py-2 text-xs font-medium text-zinc-300 hover:text-white bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-700 transition-all flex items-center justify-center gap-1.5"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Manifest Packages ({Object.keys(report.dependencies || {}).length})
          </button>
          <button
            onClick={() => router.push('/')}
            className="flex-1 sm:flex-initial px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-all flex items-center justify-center gap-1.5 shadow-md"
          >
            New Analysis
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#27272a]/60 overflow-x-auto gap-2">
        <button
          onClick={() => setActiveTab('founder_demo')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'founder_demo' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          ⚡ Founder Onboarding
        </button>
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'overview' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setActiveTab('architecture')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'architecture' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Architecture
        </button>
        <button
          onClick={() => setActiveTab('files')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'files' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Important Files
        </button>
        <button
          onClick={() => setActiveTab('onboarding')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'onboarding' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Developer Onboarding
        </button>
        <button
          onClick={() => setActiveTab('ask')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'ask' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Ask Repo
        </button>
        <button
          onClick={() => setActiveTab('tour')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'tour' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Repository Tour
        </button>
        <button
          onClick={() => setActiveTab('walkthrough')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'walkthrough' 
              ? 'border-indigo-500 text-white' 
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Architecture Walkthrough
        </button>
      </div>

      {/* Main Grid for tab content + split code viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start w-full">
        <div className={`space-y-6 ${fileViewerData ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          {/* FOUNDER DEMO TAB */}
          {activeTab === 'founder_demo' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
              {/* Left columns: summary, topology, architecture */}
              <div className="lg:col-span-2 space-y-6">
                {/* 1. Onboarding Summary & Key paradigm */}
                {report.summary && (
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4 shadow-md">
                    <div className="flex justify-between items-start gap-4">
                      <h2 className="text-base font-bold text-white flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
                        Onboarding Overview
                      </h2>
                      <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold tracking-wide ${
                        report.summary.confidence_score === 'High' 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : report.summary.confidence_score === 'Low'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                      }`}>
                        Confidence: {report.summary.confidence_score || 'Medium'}
                      </span>
                    </div>

                    <p className="text-base font-semibold text-white leading-relaxed">
                      {report.summary.project_purpose}
                    </p>

                    <p className="text-xs text-zinc-400 leading-relaxed italic">
                      <strong>Score Evaluation:</strong> {report.summary.confidence_explanation}
                    </p>

                    <div className="border-t border-zinc-800/80 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-zinc-550 font-bold block mb-1 uppercase tracking-wider">Target Contributors</span>
                        <span className="text-zinc-300 font-semibold">{report.summary.intended_contributors || 'Developers and engineering contributors.'}</span>
                      </div>
                      <div>
                        <span className="text-zinc-550 font-bold block mb-1 uppercase tracking-wider">Architecture Type</span>
                        <span className="text-zinc-300 font-semibold">{report.architecture_report?.architecture_type || 'Custom codebase structure'}</span>
                      </div>
                    </div>

                    {report.summary.major_subsystems && report.summary.major_subsystems.length > 0 && (
                      <div className="border-t border-zinc-800/80 pt-4">
                        <span className="text-zinc-550 font-bold block mb-2 uppercase tracking-wider text-xs">Major Subsystems</span>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                          {report.summary.major_subsystems.map((sub: unknown, index: number) => (
                            <div key={index} className="p-2.5 rounded bg-zinc-900 border border-zinc-850 flex gap-2 items-start text-zinc-300">
                              <svg className="w-4 h-4 text-indigo-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                              </svg>
                              <span>{toStr(sub)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {report.summary.unique_concepts && report.summary.unique_concepts.length > 0 && (
                      <div className="border-t border-zinc-800/80 pt-4">
                        <span className="text-zinc-550 font-bold block mb-2 uppercase tracking-wider text-xs">Key Architecture Paradigms</span>
                        <div className="flex flex-wrap gap-2">
                          {report.summary.unique_concepts.map((concept: unknown, index: number) => (
                            <span key={index} className="px-2.5 py-1 rounded bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 font-medium">
                              {toStr(concept)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Interactive Topology Call Graph */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4 shadow-md">
                  <div>
                    <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
                      <svg className="w-4.5 h-4.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11 3.055A9.003 9.003 0 1020.945 13H11V3.055z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                      </svg>
                      Interactive Codebase Topology Map
                    </h2>
                    <p className="text-xs text-zinc-500 mt-1">Layered calling structure. Click any node to dynamically retrieve detailed LLM explanations of its duties, dependencies, and value.</p>
                  </div>

                  {loadingGraph ? (
                    <div className="h-[450px] flex flex-col items-center justify-center gap-3 text-center">
                      <svg className="animate-spin h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <p className="text-zinc-550 text-xs">Assembling calling nodes and links...</p>
                    </div>
                  ) : graphData ? (
                    <div className="relative border border-zinc-800/80 rounded-xl overflow-hidden bg-zinc-950/40">
                      <svg viewBox="0 0 800 450" className="w-full h-auto select-none">
                        <defs>
                          <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#3f3f46" />
                          </marker>
                        </defs>
                        
                        {/* Edges */}
                        {(() => {
                          const getCoords = (nodeId: string) => {
                            const node = graphData.nodes.find(n => n.id === nodeId);
                            if (!node) return { x: 400, y: 225 };
                            let x = 400;
                            let list = [];
                            if (node.type === 'entrypoint') { x = 100; list = graphData.nodes.filter(n => n.type === 'entrypoint'); }
                            else if (node.type === 'router') { x = 300; list = graphData.nodes.filter(n => n.type === 'router'); }
                            else if (node.type === 'service') { x = 500; list = graphData.nodes.filter(n => n.type === 'service'); }
                            else if (node.type === 'database') { x = 700; list = graphData.nodes.filter(n => n.type === 'database'); }
                            const idx = list.findIndex(n => n.id === nodeId);
                            const y = list.length > 1 ? 50 + (idx * 350) / (list.length - 1) : 225;
                            return { x, y };
                          };

                          return graphData.edges.map((edge, idx) => {
                            const start = getCoords(edge.source);
                            const end = getCoords(edge.target);
                            return (
                              <g key={idx}>
                                <line
                                  x1={start.x}
                                  y1={start.y}
                                  x2={end.x}
                                  y2={end.y}
                                  stroke="#27272a"
                                  strokeWidth="1.5"
                                  markerEnd="url(#arrow)"
                                />
                                <text
                                  x={(start.x + end.x) / 2}
                                  y={(start.y + end.y) / 2 - 4}
                                  fill="#52525b"
                                  fontSize="8"
                                  textAnchor="middle"
                                  className="pointer-events-none font-mono"
                                >
                                  {edge.label}
                                </text>
                              </g>
                            );
                          });
                        })()}

                        {/* Nodes */}
                        {(() => {
                          const getCoords = (nodeId: string) => {
                            const node = graphData.nodes.find(n => n.id === nodeId);
                            if (!node) return { x: 400, y: 225 };
                            let x = 400;
                            let list = [];
                            if (node.type === 'entrypoint') { x = 100; list = graphData.nodes.filter(n => n.type === 'entrypoint'); }
                            else if (node.type === 'router') { x = 300; list = graphData.nodes.filter(n => n.type === 'router'); }
                            else if (node.type === 'service') { x = 500; list = graphData.nodes.filter(n => n.type === 'service'); }
                            else if (node.type === 'database') { x = 700; list = graphData.nodes.filter(n => n.type === 'database'); }
                            const idx = list.findIndex(n => n.id === nodeId);
                            const y = list.length > 1 ? 50 + (idx * 350) / (list.length - 1) : 225;
                            return { x, y };
                          };

                          return graphData.nodes.map(node => {
                            const { x, y } = getCoords(node.id);
                            let color = '#3b82f6'; // blue (entrypoint)
                            if (node.type === 'router') color = '#a855f7'; // purple
                            if (node.type === 'service') color = '#10b981'; // green
                            if (node.type === 'database') color = '#f97316'; // orange

                            const isSelected = selectedNodeId === node.id;

                            return (
                              <g 
                                key={node.id} 
                                transform={`translate(${x}, ${y})`}
                                className="cursor-pointer group"
                                onClick={() => handleNodeClick(node.id, node.type)}
                              >
                                <circle
                                  r="13"
                                  fill="#09090b"
                                  stroke={isSelected ? '#6366f1' : color}
                                  strokeWidth={isSelected ? '3' : '2'}
                                  className="transition-all duration-200 group-hover:scale-110"
                                />
                                <circle r="4" fill={color} />
                                <text
                                  y="25"
                                  fill="#f4f4f5"
                                  fontSize="9"
                                  fontWeight="600"
                                  textAnchor="middle"
                                  className="font-mono bg-zinc-950 px-1 select-none pointer-events-none"
                                >
                                  {node.label}
                                </text>
                                <text
                                  y="33"
                                  fill="#52525b"
                                  fontSize="7"
                                  textAnchor="middle"
                                  className="font-sans select-none pointer-events-none"
                                >
                                  {node.type.toUpperCase()}
                                </text>
                              </g>
                            );
                          });
                        })()}
                      </svg>
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-555 py-4 text-center">No topology relationships found.</p>
                  )}

                  {/* Node explainer card below graph */}
                  {(selectedNodeId || loadingExplanation) && (
                    <div className="bg-zinc-950 p-5 rounded-xl border border-zinc-800 space-y-4">
                      <div className="flex justify-between items-center border-b border-zinc-850 pb-2.5">
                        <span className="text-xs font-mono font-bold text-white truncate max-w-[400px]">
                          🔎 Explain Asset: {selectedNodeId}
                        </span>
                        <button
                          onClick={() => {
                            setSelectedNodeId(null);
                            setNodeExplanation(null);
                          }}
                          className="text-zinc-500 hover:text-white text-[10px] font-sans"
                        >
                          Clear
                        </button>
                      </div>

                      {loadingExplanation ? (
                        <div className="flex items-center gap-2 text-xs text-zinc-550 py-4 animate-pulse">
                          <svg className="animate-spin h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          <span>Analyzing file structure and compiling explanation...</span>
                        </div>
                      ) : nodeExplanation ? (
                        <div className="space-y-3.5 text-xs text-zinc-300">
                          <div>
                            <strong className="text-white block mb-0.5">Asset Purpose</strong>
                            <p>{nodeExplanation.purpose}</p>
                          </div>

                          {nodeExplanation.responsibilities && nodeExplanation.responsibilities.length > 0 && (
                            <div>
                              <strong className="text-white block mb-1">Key Responsibilities</strong>
                              <ul className="list-disc pl-4 space-y-0.5">
                                {nodeExplanation.responsibilities.map((r: string, index: number) => (
                                  <li key={index}>{r}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {nodeExplanation.key_functions && nodeExplanation.key_functions.length > 0 && (
                            <div>
                              <strong className="text-white block mb-1">Key Methods & Classes</strong>
                              <div className="flex flex-wrap gap-1.5 pt-0.5">
                                {nodeExplanation.key_functions.map((f: string, index: number) => (
                                  <span key={index} className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-850 font-mono text-[10px] text-zinc-400">
                                    {f}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {nodeExplanation.dependencies && nodeExplanation.dependencies.length > 0 && (
                            <div>
                              <strong className="text-white block mb-1">Imported Modules</strong>
                              <div className="flex flex-wrap gap-1.5 pt-0.5">
                                {nodeExplanation.dependencies.map((d: string, index: number) => (
                                  <span key={index} className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-850 font-mono text-[10px] text-zinc-400">
                                    {d}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {nodeExplanation.related_paths && nodeExplanation.related_paths.length > 0 && (
                            <div>
                              <strong className="text-white block mb-1">Related Code Paths</strong>
                              <div className="flex flex-wrap gap-1.5 pt-0.5">
                                {nodeExplanation.related_paths.map((p: string, index: number) => (
                                  <button
                                    key={index}
                                    onClick={() => handleNodeClick(p, 'file')}
                                    className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 font-mono text-[10px] text-indigo-400 hover:bg-indigo-500/20 transition-all text-left"
                                  >
                                    {p.split('/').pop()}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                          <div className="p-3.5 rounded-lg bg-indigo-500/5 border border-indigo-500/10 mt-2">
                            <strong className="text-indigo-400 block mb-0.5 font-sans">💡 Developer Value</strong>
                            <p className="italic text-zinc-350 leading-relaxed font-sans">{nodeExplanation.developer_value}</p>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>

                {/* 3. Flowcharts & Diagrams */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-5 shadow-md">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div>
                      <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
                        <svg className="w-4.5 h-4.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                        </svg>
                        Codebase Request & Service Flowcharts
                      </h2>
                      <p className="text-xs text-zinc-500 mt-1">Synthesizing flow models representing data lifecycle layers.</p>
                    </div>

                    {/* Mermaid diagram tab switches */}
                    <div className="flex rounded-lg bg-zinc-900 border border-zinc-800 p-1 self-start sm:self-auto shrink-0">
                      <button
                        onClick={() => setActiveDiagramTab('request')}
                        className={`px-2.5 py-1 text-[10px] font-bold rounded transition-all ${
                          activeDiagramTab === 'request'
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        Request Flow
                      </button>
                      <button
                        onClick={() => setActiveDiagramTab('service')}
                        className={`px-2.5 py-1 text-[10px] font-bold rounded transition-all ${
                          activeDiagramTab === 'service'
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        Services
                      </button>
                      <button
                        onClick={() => setActiveDiagramTab('folder')}
                        className={`px-2.5 py-1 text-[10px] font-bold rounded transition-all ${
                          activeDiagramTab === 'folder'
                            ? 'bg-indigo-600 text-white shadow-sm'
                            : 'text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        Folders
                      </button>
                    </div>
                  </div>

                  {loadingDiagrams ? (
                    <div className="h-[250px] flex flex-col items-center justify-center gap-3 text-center">
                      <svg className="animate-spin h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <p className="text-zinc-555 text-xs">Generating layout structures...</p>
                    </div>
                  ) : diagrams ? (
                    <div>
                      {activeDiagramTab === 'request' && (
                        <MermaidRenderer chart={diagrams.request_flow} />
                      )}
                      {activeDiagramTab === 'service' && (
                        <MermaidRenderer chart={diagrams.service_interaction} />
                      )}
                      {activeDiagramTab === 'folder' && (
                        <MermaidRenderer chart={diagrams.folder_relationship} />
                      )}
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-555 text-center py-6">Failed to load diagrams.</p>
                  )}
                </div>
              </div>

              {/* Right Column: Observability badges, Onboarding tour steps, suggested ask */}
              <div className="space-y-6">
                {/* 1. Observability Badges */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-5 space-y-4 shadow-md">
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">⏱️ Indexing & Observability Metrics</h3>
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-zinc-450">
                    <div className="p-3 bg-zinc-900 border border-zinc-850 rounded-xl space-y-1">
                      <span className="text-zinc-550 font-bold block uppercase tracking-wider">Cloning</span>
                      <strong className="text-sm text-white font-mono">{report.metrics?.latency?.clone_time || '0.8'}s</strong>
                    </div>
                    <div className="p-3 bg-zinc-900 border border-zinc-850 rounded-xl space-y-1">
                      <span className="text-zinc-555 font-bold block uppercase tracking-wider">Analyzing</span>
                      <strong className="text-sm text-white font-mono">{report.metrics?.latency?.analyze_time || '1.4'}s</strong>
                    </div>
                    <div className="p-3 bg-zinc-900 border border-zinc-850 rounded-xl space-y-1">
                      <span className="text-zinc-555 font-bold block uppercase tracking-wider">Indexing</span>
                      <strong className="text-sm text-white font-mono">{report.metrics?.latency?.indexing_time || '2.1'}s</strong>
                    </div>
                    <div className="p-3 bg-zinc-900 border border-zinc-850 rounded-xl space-y-1">
                      <span className="text-zinc-555 font-bold block uppercase tracking-wider">Total Duration</span>
                      <strong className="text-sm text-indigo-400 font-mono">{report.metrics?.latency?.total_time || '4.3'}s</strong>
                    </div>
                  </div>
                  <div className="p-3 bg-zinc-900 border border-zinc-850 rounded-xl flex items-center justify-between text-[11px] text-zinc-400">
                    <span>LLM Engine Provider:</span>
                    <strong className="text-indigo-400 font-mono">{report.summary?.llm_provider || 'gemini-2.5-flash-lite'}</strong>
                  </div>
                </div>

                {/* 2. 60 Second Tour Steps list */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-5 space-y-4 shadow-md">
                  <div className="space-y-0.5">
                    <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">🧭 60-Second Onboarding Tour</h3>
                    <p className="text-[10px] text-zinc-500 leading-normal">Sequential files roadmap. Click any path to view implementation details.</p>
                  </div>

                  {loadingTour ? (
                    <div className="flex items-center gap-2 text-[10px] text-zinc-555 py-3 animate-pulse">
                      <svg className="animate-spin h-3.5 w-3.5 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Compiling tour roadmaps...</span>
                    </div>
                  ) : tourSteps.length > 0 ? (
                    <div className="space-y-2.5">
                      {tourSteps.slice(0, 5).map((step) => (
                        <div key={step.step} className="p-3 bg-zinc-900/60 border border-zinc-850 rounded-xl hover:border-zinc-800 transition-all flex gap-3 items-start">
                          <span className="w-5 h-5 rounded-full bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center font-bold text-[10px] text-indigo-400 shrink-0 mt-0.5">
                            {step.step}
                          </span>
                          <div className="space-y-1 min-w-0 flex-1">
                            <button
                              onClick={() => handleCitationClick(step.file, 1, 100)}
                              className="text-left font-mono text-xs text-indigo-400 hover:underline font-bold truncate block w-full bg-transparent border-none p-0 cursor-pointer"
                            >
                              {step.file.split('/').pop()}
                            </button>
                            <p className="text-[11px] text-zinc-400 leading-relaxed truncate-2-lines">{step.reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-555 text-[11px] text-center py-2">No tour steps mapped.</p>
                  )}
                </div>

                {/* 3. Suggested questions */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-5 space-y-3.5 shadow-md">
                  <div className="space-y-0.5">
                    <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">💡 Suggested Ask Prompts</h3>
                    <p className="text-[10px] text-zinc-500 leading-normal">Click any prompt to instantly query the repository RAG database.</p>
                  </div>
                  
                  <div className="space-y-2">
                    {[
                      "Explain request routing structure.",
                      "Where is database connection setup?",
                      "What dependencies does this app run on?",
                      "How are business rules separated?"
                    ].map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setChatInput(q);
                          setActiveTab('ask');
                          setChatHistory((prev) => [...prev, { sender: 'user', text: q }]);
                          setAsking(true);
                          askQuestion(id, q)
                            .then((res) => {
                              setChatHistory((prev) => [
                                ...prev,
                                { sender: 'assistant', text: res.answer, citations: res.citations }
                              ]);
                            })
                            .catch((err) => {
                              setChatHistory((prev) => [
                                ...prev,
                                { sender: 'assistant', text: `Failed to retrieve answer: ${err.message}` }
                              ]);
                            })
                            .finally(() => {
                              setAsking(false);
                            });
                        }}
                        className="w-full text-left p-3 bg-zinc-900 border border-zinc-850 hover:bg-zinc-850/80 hover:border-zinc-800 rounded-xl text-xs text-zinc-350 hover:text-white transition-all font-semibold flex items-center justify-between cursor-pointer"
                      >
                        <span className="truncate pr-4">{q}</span>
                        <svg className="w-3.5 h-3.5 text-zinc-650 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                        </svg>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* OVERVIEW TAB */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                
                {/* AI Summary Box */}
                {report.summary && (
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                    <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-1.5">
                      <svg className="w-4 h-4 text-indigo-400 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      Repository Summary
                    </h2>
                    <div className="space-y-3.5 text-sm leading-relaxed text-zinc-300">
                      <p className="font-semibold text-white text-base">
                        {report.summary.project_purpose}
                      </p>
                      <p>
                        <strong className="text-zinc-400">Scale & Scope:</strong> {report.summary.repo_size}
                      </p>
                      <p>
                        <strong className="text-zinc-400">Structure Pattern:</strong> {report.summary.architecture_overview}
                      </p>
                      <div className="pt-2 flex flex-wrap gap-2">
                        {report.summary.important_modules.map((mod: unknown) => (
                          <span key={toStr(mod)} className="inline-flex items-center px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-400 font-mono">
                            {toStr(mod)}/
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Quick Metrics */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-5 space-y-1">
                    <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Total Files</p>
                    <p className="text-3xl font-extrabold text-white">{totalFiles.toLocaleString()}</p>
                  </div>
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-5 space-y-1">
                    <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wide">Lines of Code</p>
                    <p className="text-3xl font-extrabold text-white">{totalLines.toLocaleString()}</p>
                  </div>
                </div>

                {/* Languages breakdown */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-5">
                  <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Languages</h2>
                  {languagesList.length > 0 ? (
                    <div className="space-y-4">
                      <div className="w-full h-3 rounded-full flex overflow-hidden bg-zinc-800">
                        {languagesList.map(([lang, data]) => (
                          <div
                            key={lang}
                            className="h-full transition-all"
                            style={{
                              width: `${data.percentage}%`,
                              backgroundColor: LANGUAGE_COLORS[lang] || DEFAULT_LANG_COLOR
                            }}
                          />
                        ))}
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                        {languagesList.map(([lang, data]) => (
                          <div key={lang} className="flex gap-2 items-start">
                            <span className="w-3.5 h-3.5 rounded-full mt-1 shrink-0" style={{ backgroundColor: LANGUAGE_COLORS[lang] || DEFAULT_LANG_COLOR }}></span>
                            <div>
                              <p className="text-sm font-medium text-white">{lang}</p>
                              <p className="text-xs text-zinc-500">
                                {data.percentage}% ({data.lines.toLocaleString()} lines)
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-zinc-500 text-sm">No supported languages found.</p>
                  )}
                </div>
              </div>

              {/* Right Column: Frameworks & Largest files */}
              <div className="space-y-6">
                
                {/* Frameworks detected */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                  <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Frameworks</h2>
                  {report.frameworks && Object.keys(report.frameworks).length > 0 ? (
                    <div className="space-y-3">
                      {Object.entries(report.frameworks).map(([fw, score]) => (
                        <div key={fw} className="flex justify-between items-center p-3 rounded-xl bg-zinc-900 border border-zinc-800/60">
                          <span className="text-sm font-semibold text-white">{fw}</span>
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            score > 0.8 
                              ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30' 
                              : 'bg-zinc-850 text-zinc-500 border border-zinc-800'
                          }`}>
                            {Math.round(score * 100)}% Confidence
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-500 text-sm py-2">No frameworks detected.</p>
                  )}
                </div>

                {/* Top Largest Files */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                  <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Largest Files</h2>
                  <div className="space-y-3">
                    {report.metrics?.largest_files && report.metrics.largest_files.slice(0, 5).map((file) => (
                      <div key={file.path} className="flex justify-between items-start text-xs p-3 rounded-xl bg-zinc-900/40 border border-zinc-800/60">
                        <span className="font-mono text-zinc-300 truncate max-w-[150px] sm:max-w-none">{file.path}</span>
                        <span className="text-zinc-500 shrink-0 ml-2 font-mono">
                          {file.size > 1024 * 1024 
                            ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
                            : `${(file.size / 1024).toFixed(1)} KB`
                          }
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ARCHITECTURE DETECTOR TAB */}
          {activeTab === 'architecture' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {report.architecture_report ? (
                <>
                  {/* Type & Confidence Card */}
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 flex flex-col justify-between shadow-md">
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Structure Paradigm</p>
                      <h2 className="text-2xl font-extrabold text-white">{report.architecture_report.architecture_type}</h2>
                    </div>
                    
                    {/* Circular visual gauge using percentage line */}
                    <div className="py-6 flex items-center gap-4">
                      <div className="relative w-16 h-16 flex items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 shrink-0">
                        <svg className="w-full h-full transform -rotate-95 absolute inset-0">
                          <circle cx="32" cy="32" r="28" fill="none" stroke="#27272a" strokeWidth="4" />
                          <circle 
                            cx="32" 
                            cy="32" 
                            r="28" 
                            fill="none" 
                            stroke="#6366f1" 
                            strokeWidth="4" 
                            strokeDasharray={2 * Math.PI * 28}
                            strokeDashoffset={2 * Math.PI * 28 * (1 - report.architecture_report.confidence_score)}
                            strokeLinecap="round"
                          />
                        </svg>
                        <span className="text-xs font-bold text-white z-10">
                          {Math.round(report.architecture_report.confidence_score * 100)}
                        </span>
                      </div>
                      <div className="space-y-0.5">
                        <p className="text-xs font-bold text-zinc-300">Confidence Score</p>
                        <p className="text-xs text-zinc-500">Calculated via repository file mapping heuristics.</p>
                      </div>
                    </div>
                  </div>

                  {/* Evidence cards */}
                  <div className="md:col-span-2 bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                    <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Evidence & folder structural patterns</h2>
                    <div className="space-y-3.5">
                      {report.architecture_report.evidence.map((ev, index) => (
                        <div key={index} className="flex gap-3 items-start p-4 rounded-xl bg-zinc-900 border border-zinc-800">
                          <div className="w-5 h-5 rounded-full bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shrink-0 mt-0.5">
                            <svg className="w-3 h-3 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                          <p className="text-sm text-zinc-300 leading-normal">{ev}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className="col-span-3 text-center py-12 border border-dashed border-zinc-800 rounded-xl">
                  <p className="text-zinc-550 text-sm">No architecture heuristics available for this report.</p>
                </div>
              )}
            </div>
          )}

          {/* IMPORTANT FILES RANKER TAB */}
          {activeTab === 'files' && (
            <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-6 shadow-md">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-white">Top 10 Files to Read First</h2>
                <p className="text-xs text-zinc-400">Ranked by importance signals (entry points, manifests, routers, databases, configuration files).</p>
              </div>

              {report.important_files && report.important_files.length > 0 ? (
                <div className="space-y-4">
                  {report.important_files.map((file, idx) => {
                    let badgeClass = "bg-zinc-850 text-zinc-400 border border-zinc-800";
                    if (file.importance_score >= 95) {
                      badgeClass = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
                    } else if (file.importance_score >= 85) {
                      badgeClass = "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
                    } else if (file.importance_score >= 70) {
                      badgeClass = "bg-sky-500/10 text-sky-400 border border-sky-500/20";
                    }

                    return (
                      <div key={file.path} className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-zinc-700/60 transition-all">
                        <div className="space-y-1.5 min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-zinc-500 select-none">#{idx + 1}</span>
                            <button
                              onClick={() => handleCitationClick(file.path, 1, 100)}
                              className="text-sm font-semibold font-mono text-white hover:text-indigo-400 transition-colors text-left"
                            >
                              {file.path}
                            </button>
                          </div>
                          <p className="text-xs text-zinc-400 leading-normal">{file.explanation}</p>
                        </div>
                        <span className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold tracking-wide shrink-0 ${badgeClass}`}>
                          Score {file.importance_score}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-12 border border-dashed border-zinc-800 rounded-xl">
                  <p className="text-zinc-550 text-sm">No ranked files metadata available.</p>
                </div>
              )}
            </div>
          )}

          {/* DEVELOPER ONBOARDING GUIDE TAB */}
          {activeTab === 'onboarding' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Main onboarding roadmap */}
              <div className="lg:col-span-2 space-y-6">
                
                {/* Where to Start */}
                {report.onboarding_guide && (
                  <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                    <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
                      <svg className="w-4.5 h-4.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                      </svg>
                      Where to Start
                    </h2>
                    <p className="text-sm text-zinc-300 leading-relaxed">
                      {report.onboarding_guide.where_to_start}
                    </p>
                  </div>
                )}

                {/* Reading Order Timeline */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-6">
                  <div className="space-y-1">
                    <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Recommended Reading Order</h2>
                    <p className="text-xs text-zinc-500">Walk through these files sequentially to build a structural understanding of the codebase.</p>
                  </div>

                  {report.onboarding_guide && report.onboarding_guide.recommended_reading_order.length > 0 ? (
                    <div className="relative border-l border-zinc-800/80 ml-3 pl-6 space-y-6">
                      {report.onboarding_guide.recommended_reading_order.map((step) => (
                        <div key={step.step} className="relative">
                          {/* Timeline dot */}
                          <span className="absolute -left-9 top-0.5 w-5 h-5 rounded-full bg-zinc-950 border-2 border-indigo-500 flex items-center justify-center text-[10px] font-bold text-indigo-400 select-none">
                            {step.step}
                          </span>
                          <div className="space-y-1">
                            <button
                              onClick={() => handleCitationClick(step.path, 1, 100)}
                              className="text-xs font-mono font-bold text-white hover:text-indigo-400 transition-colors text-left"
                            >
                              {step.path}
                            </button>
                            <p className="text-xs text-zinc-400 leading-relaxed">{step.reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-550 text-sm">No sequential order metadata available.</p>
                  )}
                </div>
              </div>

              {/* Right column onboarding meta */}
              <div className="space-y-6">
                
                {/* Entry Points List */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                  <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Bootstrap Entrypoints</h2>
                  {report.onboarding_guide && report.onboarding_guide.entry_points.length > 0 ? (
                    <div className="space-y-3">
                      {report.onboarding_guide.entry_points.map((ep) => (
                        <div key={ep.path} className="space-y-1 p-3 rounded-xl bg-zinc-900 border border-zinc-800">
                          <button
                            onClick={() => handleCitationClick(ep.path, 1, 100)}
                            className="text-xs font-mono font-bold text-indigo-400 hover:underline text-left block"
                          >
                            {ep.path}
                          </button>
                          <p className="text-[11px] text-zinc-550 leading-normal">{ep.description}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-550 text-sm py-2">No entry points mapped.</p>
                  )}
                </div>

                {/* Folder Module Breakdown */}
                <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-4">
                  <h2 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">Folder Architecture Map</h2>
                  {report.onboarding_guide && report.onboarding_guide.important_folders.length > 0 ? (
                    <div className="space-y-3">
                      {report.onboarding_guide.important_folders.map((folder) => (
                        <div key={folder.path} className="flex gap-2.5 items-start text-xs leading-normal">
                          {/* folder icon */}
                          <svg className="w-4 h-4 text-zinc-550 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                          </svg>
                          <div>
                            <span className="font-semibold text-white block font-mono">{folder.path}/</span>
                            <span className="text-zinc-400 text-[11px]">{folder.description}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-zinc-550 text-sm py-2">No folder structure mapped.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ASK REPO TAB */}
          {activeTab === 'ask' && (
            <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-6 shadow-md h-[650px] flex flex-col justify-between">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  Ask Repository
                </h2>
                <p className="text-xs text-zinc-400">Ask questions about codebase structure, flow, or databases and get referenced answers.</p>
              </div>

              {/* Chat history */}
              <div className="flex-1 overflow-y-auto space-y-4 pr-2 p-4 bg-zinc-950/40 rounded-xl border border-zinc-800/80 scrollbar-thin">
                {chatHistory.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3">
                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                    </div>
                    <h3 className="text-sm font-semibold text-white">Ask your first question</h3>
                    <p className="text-xs text-zinc-550 max-w-xs">E.g., "How does routing work?" or "Where are the API paths registered?"</p>
                  </div>
                ) : (
                  chatHistory.map((msg, index) => (
                    <div
                      key={index}
                      className={`flex flex-col max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed ${
                        msg.sender === 'user'
                          ? 'bg-indigo-600/15 text-indigo-200 border border-indigo-500/20 self-end ml-auto'
                          : 'bg-zinc-900 border border-zinc-800 text-zinc-300 self-start mr-auto'
                      }`}
                    >
                      <span className="font-bold text-[10px] uppercase tracking-wider mb-1 block text-zinc-500">
                        {msg.sender === 'user' ? 'You' : 'Architect Expert'}
                      </span>
                      <div className="whitespace-pre-wrap">{msg.text}</div>

                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-zinc-800/80 flex flex-wrap gap-2 items-center">
                          <span className="text-[10px] text-zinc-550 font-bold uppercase tracking-wider">Citations:</span>
                          {msg.citations.map((cite, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => handleCitationClick(cite.file_path, cite.start_line, cite.end_line)}
                              className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-mono text-indigo-400 hover:bg-indigo-500/20 transition-all flex items-center gap-1"
                            >
                              {cite.file_path.split('/').pop()} ({cite.start_line}-{cite.end_line})
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}

                {asking && (
                  <div className="flex gap-2 items-center text-xs text-zinc-550 p-3 bg-zinc-900/40 rounded-xl border border-zinc-800/40 self-start mr-auto animate-pulse">
                    <svg className="animate-spin h-3.5 w-3.5 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Composing grounded response...</span>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <form onSubmit={handleAskSubmit} className="flex gap-3 mt-4 border-t border-zinc-850 pt-4 shrink-0">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask a question about authentication, database, models..."
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-xs text-white placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-all"
                  disabled={asking}
                />
                <button
                  type="submit"
                  disabled={asking || !chatInput.trim()}
                  className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 transition-all text-xs font-semibold text-white shadow-md cursor-pointer"
                >
                  Ask
                </button>
              </form>
            </div>
          )}

          {/* REPOSITORY TOUR TAB */}
          {activeTab === 'tour' && (
            <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-6 shadow-md">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                  </svg>
                  60 Second Repository Tour
                </h2>
                <p className="text-xs text-zinc-400">Step-by-step developer tour explaining files, entry points, and onboarding reasons.</p>
              </div>

              {loadingTour ? (
                <div className="py-12 flex flex-col items-center justify-center gap-3 text-center">
                  <svg className="animate-spin h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-zinc-500 text-xs">Synthesizing step-by-step onboarding roadmap...</p>
                </div>
              ) : tourSteps.length > 0 ? (
                <div className="grid grid-cols-1 gap-4">
                  {tourSteps.map((step) => (
                    <div key={step.step} className="flex gap-4 p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/60 hover:bg-zinc-900/85 transition-all">
                      <span className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500 flex items-center justify-center font-bold text-indigo-400 shrink-0 text-sm">
                        {step.step}
                      </span>
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <button
                          onClick={() => handleCitationClick(step.file, 1, 100)}
                          className="text-left font-mono text-sm text-indigo-400 hover:text-indigo-300 hover:underline font-bold truncate block max-w-full cursor-pointer bg-transparent border-none p-0"
                        >
                          {step.file}
                        </button>
                        <p className="text-zinc-300 text-xs leading-relaxed">{step.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-zinc-550 text-sm text-center py-8">Failed to compile Repository Tour steps.</p>
              )}
            </div>
          )}

          {/* ARCHITECTURE WALKTHROUGH TAB */}
          {activeTab === 'walkthrough' && (
            <div className="bg-[#121215] border border-[#27272a] rounded-2xl p-6 space-y-6 shadow-md">
              <div className="space-y-1">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  Architecture Walkthrough
                </h2>
                <p className="text-xs text-zinc-400">Detailed flows explaining request, service layers, database pipelines, and folder scopes.</p>
              </div>

              {loadingWalkthrough ? (
                <div className="py-12 flex flex-col items-center justify-center gap-3 text-center">
                  <svg className="animate-spin h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-zinc-500 text-xs">Generating architecture walkthrough guide...</p>
                </div>
              ) : walkthroughMd ? (
                <div className="p-6 bg-[#0a0a0c] border border-zinc-800/80 rounded-xl space-y-4">
                  {walkthroughMd.split('\n').map((line, idx) => {
                    if (line.startsWith('# ')) {
                      return <h1 key={idx} className="text-base font-bold text-white mt-5 mb-2 first:mt-0">{line.substring(2)}</h1>;
                    }
                    if (line.startsWith('## ')) {
                      return <h2 key={idx} className="text-sm font-bold text-indigo-400 mt-4 mb-2 border-b border-zinc-800 pb-1">{line.substring(3)}</h2>;
                    }
                    if (line.startsWith('### ')) {
                      return <h3 key={idx} className="text-xs font-bold text-zinc-200 mt-3 mb-1">{line.substring(4)}</h3>;
                    }
                    if (line.startsWith('- ') || line.startsWith('* ')) {
                      return <li key={idx} className="ml-4 list-disc text-[11px] text-zinc-400 mb-1 leading-relaxed">{line.substring(2)}</li>;
                    }
                    if (line.trim() === '') {
                      return <div key={idx} className="h-2"></div>;
                    }
                    return <p key={idx} className="text-[11px] text-zinc-350 mb-2 leading-relaxed">{line}</p>;
                  })}
                </div>
              ) : (
                <p className="text-zinc-550 text-sm text-center py-8">Failed to compile Architecture Walkthrough.</p>
              )}
            </div>
          )}
        </div>

        {/* Code Viewer Panel */}
        {fileViewerData && (
          <div className="lg:col-span-5 sticky top-8 bg-[#121215] border border-[#27272a] rounded-2xl p-5 flex flex-col h-[650px] shadow-2xl relative">
            <div className="flex justify-between items-center border-b border-zinc-850 pb-3 mb-4 shrink-0">
              <div className="min-w-0 flex-1">
                <h3 className="text-xs font-mono font-bold text-white truncate pr-4">
                  {fileViewerData.file_path}
                </h3>
                {selectedLineRange && (
                  <p className="text-[10px] text-zinc-500 font-mono mt-0.5">
                    Lines {selectedLineRange[0]}-{selectedLineRange[1]}
                  </p>
                )}
              </div>
              <button
                onClick={() => {
                  setFileViewerData(null);
                  setSelectedLineRange(null);
                }}
                className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-all text-[11px] font-semibold font-sans cursor-pointer"
              >
                Close
              </button>
            </div>
            <div className="flex-1 overflow-auto font-mono text-[11px] bg-zinc-950 p-4 rounded-xl border border-zinc-800/80 leading-relaxed text-zinc-350 scrollbar-thin">
              {fileViewerData.lines.map((line, idx) => {
                const lineNum = idx + 1;
                const isHighlighted = selectedLineRange && (lineNum >= selectedLineRange[0] && lineNum <= selectedLineRange[1]);
                return (
                  <div
                    key={lineNum}
                    className={`flex gap-4 px-2 py-0.5 rounded transition-all ${
                      isHighlighted ? 'bg-indigo-500/10 border-l-2 border-indigo-500 text-white font-semibold' : ''
                    }`}
                  >
                    <span className="w-8 select-none text-right text-zinc-650 pr-2 shrink-0">
                      {lineNum}
                    </span>
                    <pre className="whitespace-pre">{line}</pre>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* DRAWER MODAL FOR PROJECTS DEPENDENCIES */}
      {showDeps && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm transition-all duration-300">
          <div className="w-full max-w-xl h-full bg-[#121215] border-l border-[#27272a] p-6 overflow-y-auto flex flex-col justify-between shadow-2xl relative">
            <div className="space-y-6">
              
              {/* Header */}
              <div className="flex justify-between items-start border-b border-zinc-800/80 pb-4">
                <div className="space-y-1">
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    Dependencies Manifests
                  </h2>
                  <p className="text-xs text-zinc-500">Libraries parsed from configuration file manifests.</p>
                </div>
                <button 
                  onClick={() => setShowDeps(false)}
                  className="p-1 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-all"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Manifest tables */}
              {report.dependencies && Object.keys(report.dependencies).length > 0 ? (
                <div className="space-y-5">
                  {Object.entries(report.dependencies).map(([manifest, deps]) => (
                    <div key={manifest} className="border border-zinc-800/80 rounded-xl overflow-hidden text-xs">
                      <div className="bg-zinc-900 px-4 py-2.5 flex items-center justify-between border-b border-zinc-800">
                        <span className="font-mono font-bold text-white truncate max-w-[300px]">{manifest}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-zinc-850 text-zinc-400">
                          {deps.length}
                        </span>
                      </div>
                      
                      {deps.length > 0 ? (
                        <div className="max-h-[200px] overflow-y-auto divide-y divide-zinc-850">
                          {deps.map((dep: DependencyItem) => (
                            <div key={dep.name} className="flex justify-between items-center px-4 py-2 hover:bg-zinc-800/10">
                              <span className="font-semibold text-white truncate max-w-[250px]">{dep.name}</span>
                              <span className="font-mono text-zinc-400 text-[11px] shrink-0 ml-2">{dep.version || 'any'}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-4 text-center text-zinc-500 italic">No libraries parsed.</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 border border-dashed border-zinc-800 rounded-xl text-zinc-500 text-sm">
                  No dependency manifest parsed.
                </div>
              )}
            </div>
            
            <button
              onClick={() => setShowDeps(false)}
              className="w-full mt-6 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 font-medium hover:text-white transition-all hover:bg-zinc-850"
            >
              Close
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
