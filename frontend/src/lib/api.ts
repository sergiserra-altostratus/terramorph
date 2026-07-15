const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface HealthResponse {
  status: string;
  version: string;
  gcp_authenticated: boolean;
}

export interface UsageStats {
  by_resource_type: Record<string, number>;
  total_generated: number;
  total_jobs: number;
  recent_jobs: Array<{
    timestamp: string;
    total_resources: number;
    types: Record<string, number>;
  }>;
}

export interface AuthStatus {
  authenticated: boolean;
  project: string | null;
  account: string | null;
}

export interface Project {
  project_id: string;
  name: string;
  state: string;
  parent: string;
}

export interface DiscoveryRequest {
  scope: { type: string; id: string };
  resource_types: string[];
}

export interface DiscoveryJob {
  job_id: string;
  status: string;
}

export interface JobProgress {
  total: number;
  completed: number;
  current_type: string | null;
  message: string;
}

export interface DiscoveryStatus {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: JobProgress;
  resources_found: number;
  error: string | null;
}

export interface DiscoveredResource {
  id: string;
  type: string;
  name: string;
  project: string;
  location: string;
  terraform_resource_type: string;
  terraform_resource_name: string;
  terraform_import_id: string;
  attributes: Record<string, unknown>;
}

export interface ResourceSummary {
  compute_instance: number;
  vpc_network: number;
  subnet: number;
  gcs_bucket: number;
  cloud_sql: number;
  gke_cluster: number;
}

export interface DiscoveryResult {
  job_id: string;
  status: string;
  resources: DiscoveredResource[];
  summary: ResourceSummary;
}

export interface GenerationRequest {
  job_id: string;
  resource_ids: string[];
  options: {
    include_provider_block: boolean;
    include_import_script: boolean;
    output_format: "single_file" | "per_resource_type";
    generation_style: "flat" | "module";
    backend_state?: {
      bucket: string;
      prefix: string;
    };
  };
}

export interface GeneratedFile {
  filename: string;
  content: string;
}

export interface GenerationResult {
  files: GeneratedFile[];
  total_resources: number;
  import_commands: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
    return response.json();
  }

  async getHealth(): Promise<HealthResponse> {
    return this.request("/health");
  }

  async getStats(): Promise<UsageStats> {
    return this.request("/stats");
  }

  async getAuthStatus(): Promise<AuthStatus> {
    return this.request("/auth/status");
  }

  async listProjects(parent?: string): Promise<{ projects: Project[] }> {
    const params = parent ? `?parent=${encodeURIComponent(parent)}` : "";
    return this.request(`/projects${params}`);
  }

  async startDiscovery(request: DiscoveryRequest): Promise<DiscoveryJob> {
    return this.request("/discovery/start", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async getDiscoveryStatus(jobId: string): Promise<DiscoveryStatus> {
    return this.request(`/discovery/status/${jobId}`);
  }

  async getDiscoveryResults(jobId: string): Promise<DiscoveryResult> {
    return this.request(`/discovery/results/${jobId}`);
  }

  async generateTerraform(request: GenerationRequest): Promise<GenerationResult> {
    return this.request("/generate/terraform", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  getDownloadUrl(jobId: string): string {
    return `${this.baseUrl}/generate/download/${jobId}`;
  }

  getWebSocketUrl(jobId: string): string {
    const wsBase = this.baseUrl
      .replace("http://", "ws://")
      .replace("https://", "wss://")
      .replace("/api/v1", "");
    return `${wsBase}/ws/discovery/${jobId}`;
  }
}

export const apiClient = new ApiClient(API_URL);
