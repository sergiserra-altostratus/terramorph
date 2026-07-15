use reqwest::Client;
use serde::{Deserialize, Serialize};

pub struct ApiClient {
    base_url: String,
    client: Client,
}

#[derive(Deserialize, Debug)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub gcp_authenticated: bool,
}

#[derive(Serialize)]
pub struct DiscoveryRequest {
    pub scope: Scope,
    pub resource_types: Vec<String>,
}

#[derive(Serialize)]
pub struct Scope {
    #[serde(rename = "type")]
    pub scope_type: String,
    pub id: String,
}

#[derive(Deserialize, Debug)]
pub struct DiscoveryJob {
    pub job_id: String,
    pub status: String,
}

#[derive(Deserialize, Debug)]
pub struct JobProgress {
    pub total: u32,
    pub completed: u32,
    pub current_type: Option<String>,
    pub message: String,
}

#[derive(Deserialize, Debug)]
pub struct DiscoveryStatus {
    pub job_id: String,
    pub status: String,
    pub progress: JobProgress,
    pub resources_found: u32,
    pub error: Option<String>,
}

#[derive(Deserialize, Debug)]
pub struct DiscoveredResource {
    pub id: String,
    #[serde(rename = "type")]
    pub resource_type: String,
    pub name: String,
    pub project: String,
    pub location: String,
    pub terraform_resource_type: String,
    pub terraform_resource_name: String,
}

#[derive(Deserialize, Debug)]
pub struct DiscoveryResult {
    pub job_id: String,
    pub status: String,
    pub resources: Vec<DiscoveredResource>,
}

#[derive(Serialize)]
pub struct GenerationRequest {
    pub job_id: String,
    pub resource_ids: Vec<String>,
    pub options: GenerationOptions,
}

#[derive(Serialize)]
pub struct GenerationOptions {
    pub include_provider_block: bool,
    pub include_import_script: bool,
    pub output_format: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub backend_state: Option<BackendStateConfig>,
}

#[derive(Serialize)]
pub struct BackendStateConfig {
    pub bucket: String,
    pub prefix: String,
}

#[derive(Deserialize, Debug)]
pub struct GeneratedFile {
    pub filename: String,
    pub content: String,
}

#[derive(Deserialize, Debug)]
pub struct GenerationResult {
    pub files: Vec<GeneratedFile>,
    pub total_resources: u32,
    pub import_commands: u32,
}

impl ApiClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client: Client::new(),
        }
    }

    pub async fn health(&self) -> Result<HealthResponse, Box<dyn std::error::Error>> {
        let resp = self.client
            .get(format!("{}/health", self.base_url))
            .send()
            .await?
            .json::<HealthResponse>()
            .await?;
        Ok(resp)
    }

    pub async fn start_discovery(&self, req: &DiscoveryRequest) -> Result<DiscoveryJob, Box<dyn std::error::Error>> {
        let resp = self.client
            .post(format!("{}/discovery/start", self.base_url))
            .json(req)
            .send()
            .await?
            .json::<DiscoveryJob>()
            .await?;
        Ok(resp)
    }

    pub async fn get_status(&self, job_id: &str) -> Result<DiscoveryStatus, Box<dyn std::error::Error>> {
        let resp = self.client
            .get(format!("{}/discovery/status/{}", self.base_url, job_id))
            .send()
            .await?
            .json::<DiscoveryStatus>()
            .await?;
        Ok(resp)
    }

    pub async fn get_results(&self, job_id: &str) -> Result<DiscoveryResult, Box<dyn std::error::Error>> {
        let resp = self.client
            .get(format!("{}/discovery/results/{}", self.base_url, job_id))
            .send()
            .await?
            .json::<DiscoveryResult>()
            .await?;
        Ok(resp)
    }

    pub async fn generate(&self, req: &GenerationRequest) -> Result<GenerationResult, Box<dyn std::error::Error>> {
        let resp = self.client
            .post(format!("{}/generate/terraform", self.base_url))
            .json(req)
            .send()
            .await?
            .json::<GenerationResult>()
            .await?;
        Ok(resp)
    }
}
