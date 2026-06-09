export interface LargestFile {
  path: string;
  extension: string;
  size: number;
  line_count: number;
}

export interface LatencyMetric {
  clone_time: number;
  analyze_time: number;
  indexing_time: number;
  total_time: number;
}

export interface RepositoryMetrics {
  total_files: number;
  total_lines: number;
  largest_files: LargestFile[];
  latency?: LatencyMetric;
}

export interface LanguageMetric {
  files: number;
  lines: number;
  percentage: number;
}

export interface LanguageBreakdown {
  [languageName: string]: LanguageMetric;
}

export interface FrameworkConfidence {
  [frameworkName: string]: number; // score between 0.0 and 1.0
}

export interface EntryPoint {
  path: string;
  language: string;
  description: string;
  confidence: number;
}

export interface DependencyItem {
  name: string;
  version: string;
  scope: string;
}

export interface DependencyList {
  [manifestPath: string]: DependencyItem[];
}

export interface RepositorySummary {
  project_purpose: string;
  main_technologies: string[];
  main_frameworks: string[];
  repo_size: string;
  important_modules: string[];
  architecture_overview: string;
  confidence_score?: string;
  confidence_explanation?: string;
  intended_contributors?: string;
  major_subsystems?: string[];
  unique_concepts?: string[];
  llm_provider?: string;
}

export interface ArchitectureReport {
  architecture_type: string;
  confidence_score: number;
  evidence: string[];
}

export interface ImportantFile {
  path: string;
  importance_score: number;
  explanation: string;
}

export interface OnboardingFolder {
  path: string;
  description: string;
}

export interface OnboardingReadingStep {
  step: number;
  path: string;
  reason: string;
}

export interface OnboardingGuide {
  where_to_start: string;
  entry_points: {
    path: string;
    language: string;
    description: string;
  }[];
  important_folders: OnboardingFolder[];
  recommended_reading_order: OnboardingReadingStep[];
  key_technologies: string[];
}

export type AnalysisStatus = 'pending' | 'cloning' | 'analyzing' | 'completed' | 'failed';

export interface AnalysisReport {
  id: string;
  github_url: string;
  repo_owner: string | null;
  repo_name: string | null;
  status: AnalysisStatus;
  error_message: string | null;
  metrics: RepositoryMetrics | null;
  languages: LanguageBreakdown | null;
  frameworks: FrameworkConfidence | null;
  entry_points: EntryPoint[] | null;
  dependencies: DependencyList | null;
  summary: RepositorySummary | null;
  architecture_report: ArchitectureReport | null;
  important_files: ImportantFile[] | null;
  onboarding_guide: OnboardingGuide | null;
  repository_tour: TourResponse | null;
  architecture_walkthrough: WalkthroughResponse | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
}

export interface TourStep {
  step: number;
  file: string;
  reason: string;
}

export interface TourResponse {
  tour_steps: TourStep[];
  raw_text: string;
}

export interface WalkthroughResponse {
  walkthrough: string;
}

