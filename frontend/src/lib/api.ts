const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface HealthResponse {
  status: string;
  version: string;
  gcp_authenticated: boolean;
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
    ai_clean: boolean;
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

  async request<T>(path: string, options?: RequestInit): Promise<T> {
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

  async getAISettings(): Promise<any> {
    return this.request("/settings/ai");
  }

  async getAIStatus(): Promise<{ configured: boolean }> {
    return this.request("/settings/ai/status");
  }

  async configureAIProvider(data: { provider: string; api_key: string; model: string; endpoint_url: string }): Promise<any> {
    return this.request("/settings/ai/configure", { method: "POST", body: JSON.stringify(data) });
  }

  async activateAIProvider(provider: string): Promise<any> {
    return this.request("/settings/ai/activate", { method: "POST", body: JSON.stringify({ provider }) });
  }

  async removeAIProvider(provider: string): Promise<any> {
    return this.request(`/settings/ai/${provider}`, { method: "DELETE" });
  }

  async getDriftPrerequisites(): Promise<{ ai_configured: boolean; ai_provider: string | null; ready: boolean; missing: string[] }> {
    return this.request("/drift/prerequisites");
  }

  async startDriftDetection(data: { tf_files: Record<string, string>; bucket: string; prefix: string; project_id: string }): Promise<{ job_id: string; status: string }> {
    return this.request("/drift/start", { method: "POST", body: JSON.stringify(data) });
  }

  async getDriftStatus(jobId: string): Promise<any> {
    return this.request(`/drift/status/${jobId}`);
  }

  async getDriftResults(jobId: string): Promise<any> {
    return this.request(`/drift/results/${jobId}`);
  }

  async getBulkExportAvailability(): Promise<{ available: boolean; resource_types: string[]; total_types: number }> {
    return this.request("/bulk-export/available");
  }

  async checkCloudAssetAPI(projectId: string): Promise<{ enabled: boolean; message?: string; error?: string }> {
    return this.request(`/bulk-export/check-api/${encodeURIComponent(projectId)}`);
  }

  async startBulkExport(data: { project_id: string; resource_types?: string[] }): Promise<{ job_id: string; status: string }> {
    return this.request("/bulk-export/start", { method: "POST", body: JSON.stringify(data) });
  }

  async getBulkExportStatus(jobId: string): Promise<any> {
    return this.request(`/bulk-export/status/${jobId}`);
  }

  async getBulkExportResults(jobId: string): Promise<any> {
    return this.request(`/bulk-export/results/${jobId}`);
  }

  // AWS
  async getAWSSettings(): Promise<any> {
    return this.request("/settings/aws");
  }

  async configureAWS(data: { access_key_id: string; secret_access_key: string; region: string; session_token?: string }): Promise<any> {
    return this.request("/settings/aws/configure", { method: "POST", body: JSON.stringify(data) });
  }

  async removeAWS(): Promise<any> {
    return this.request("/settings/aws", { method: "DELETE" });
  }

  async verifyAWS(): Promise<any> {
    return this.request("/settings/aws/verify");
  }

  async getAWSStatus(): Promise<{ configured: boolean }> {
    return this.request("/settings/aws/status");
  }

  async getAWSResourceTypes(): Promise<{ types: Array<{ value: string; label: string }>; total: number }> {
    return this.request("/aws/discovery/types");
  }

  async startAWSDiscovery(data: { resource_types: string[] }): Promise<{ job_id: string; status: string }> {
    return this.request("/aws/discovery/start", { method: "POST", body: JSON.stringify(data) });
  }

  async getAWSDiscoveryStatus(jobId: string): Promise<any> {
    return this.request(`/aws/discovery/status/${jobId}`);
  }

  async getAWSDiscoveryResults(jobId: string): Promise<any> {
    return this.request(`/aws/discovery/results/${jobId}`);
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
