import { AnalysisReport, AskResponse, TourResponse, WalkthroughResponse } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AnalyzeResponse {
  report_id: string;
  status: string;
  message: string;
}

export async function analyzeRepository(githubUrl: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ github_url: githubUrl }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to submit repository for analysis.');
  }

  return response.json();
}

export async function getReport(reportId: string): Promise<AnalysisReport> {
  const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store' // Ensure we get fresh status updates when polling
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch analysis report: ${reportId}`);
  }

  return response.json();
}

export async function askQuestion(reportId: string, question: string): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to submit question to repository.');
  }

  return response.json();
}

export async function getTour(reportId: string): Promise<TourResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/tour`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to retrieve repository tour.');
  }

  return response.json();
}

export async function getWalkthrough(reportId: string): Promise<WalkthroughResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/architecture-walkthrough`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to retrieve architecture walkthrough.');
  }

  return response.json();
}

export async function getFileContent(reportId: string, path: string): Promise<{ file_path: string; content: string; lines: string[] }> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/file?path=${encodeURIComponent(path)}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to retrieve file content: ${path}`);
  }

  return response.json();
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ExplanationResponse {
  purpose: string;
  responsibilities: string[];
  key_functions: string[];
  dependencies: string[];
  related_paths: string[];
  developer_value: string;
}

export interface DiagramsResponse {
  request_flow: string;
  service_interaction: string;
  folder_relationship: string;
}

export async function getGraph(reportId: string): Promise<GraphResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/graph`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to retrieve repository relationship graph.');
  }

  return response.json();
}

export async function getExplanation(reportId: string, path: string, type: 'file' | 'folder'): Promise<ExplanationResponse> {
  const endpoint = type === 'file' ? 'explain-file' : 'explain-folder';
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/${endpoint}?path=${encodeURIComponent(path)}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to retrieve explanation for ${type}: ${path}`);
  }

  return response.json();
}

export async function getDiagrams(reportId: string): Promise<DiagramsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${reportId}/diagrams`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
    cache: 'no-store'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to retrieve architecture diagrams.');
  }

  return response.json();
}


