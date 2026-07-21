use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub struct ApiClient {
    base_url: String,
    client: Client,
}

// === Health ===

#[derive(Deserialize, Debug)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub gcp_authenticated: bool,
}

// === Discovery ===

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

// === Generation ===

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
    pub generation_style: String,
    pub ai_clean: bool,
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

// === Bulk Export ===

#[derive(Deserialize, Debug)]
pub struct BulkExportAvailability {
    pub available: bool,
    pub total_types: u32,
}

#[derive(Deserialize, Debug)]
pub struct ApiCheckResult {
    pub enabled: bool,
    pub message: Option<String>,
}

#[derive(Deserialize, Debug)]
pub struct BulkExportResult {
    pub job_id: String,
    pub status: String,
    pub resources: Vec<serde_json::Value>,
    pub tf_files: HashMap<String, String>,
}

// === Drift ===

#[derive(Deserialize, Debug)]
pub struct DriftPrerequisites {
    pub ai_configured: bool,
    pub ai_provider: Option<String>,
    pub ready: bool,
    pub missing: Vec<String>,
}

#[derive(Deserialize, Debug)]
pub struct DriftJob {
    pub job_id: String,
    pub status: String,
}

#[derive(Deserialize, Debug)]
pub struct DriftProgress {
    pub iteration: u32,
    pub max_iterations: u32,
    pub message: String,
}

#[derive(Deserialize, Debug)]
pub struct DriftStatus {
    pub job_id: String,
    pub status: String,
    pub progress: DriftProgress,
    pub error: Option<String>,
}

#[derive(Deserialize, Debug)]
pub struct DriftResultData {
    pub message: String,
    pub iterations_needed: Option<u32>,
    pub final_files: Option<HashMap<String, String>>,
}

#[derive(Deserialize, Debug)]
pub struct DriftResults {
    pub job_id: String,
    pub status: String,
    pub result: Option<DriftResultData>,
    pub error: Option<String>,
}

// === AI Settings ===

#[derive(Deserialize, Debug)]
pub struct AIStatus {
    pub configured: bool,
}

// === Implementation ===

impl ApiClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            client: Client::new(),
        }
    }

    // Health
    pub async fn health(&self) -> Result<HealthResponse, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/health", self.base_url))
            .send().await?.json().await?)
    }

    pub async fn ai_status(&self) -> Result<AIStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/settings/ai/status", self.base_url))
            .send().await?.json().await?)
    }

    // Discovery
    pub async fn start_discovery(&self, scope_type: &str, scope_id: &str, resource_types: &[String]) -> Result<DiscoveryJob, Box<dyn std::error::Error>> {
        let req = DiscoveryRequest {
            scope: Scope { scope_type: scope_type.to_string(), id: scope_id.to_string() },
            resource_types: resource_types.to_vec(),
        };
        Ok(self.client.post(format!("{}/discovery/start", self.base_url))
            .json(&req).send().await?.json().await?)
    }

    pub async fn get_discovery_status(&self, job_id: &str) -> Result<DiscoveryStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/discovery/status/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    pub async fn get_discovery_results(&self, job_id: &str) -> Result<DiscoveryResult, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/discovery/results/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    // Generation
    pub async fn generate(&self, req: &GenerationRequest) -> Result<GenerationResult, Box<dyn std::error::Error>> {
        Ok(self.client.post(format!("{}/generate/terraform", self.base_url))
            .json(req).send().await?.json().await?)
    }

    // Bulk Export
    pub async fn get_bulk_export_availability(&self) -> Result<BulkExportAvailability, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/bulk-export/available", self.base_url))
            .send().await?.json().await?)
    }

    pub async fn check_cloud_asset_api(&self, project_id: &str) -> Result<ApiCheckResult, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/bulk-export/check-api/{}", self.base_url, project_id))
            .send().await?.json().await?)
    }

    pub async fn start_bulk_export(&self, project_id: &str) -> Result<DiscoveryJob, Box<dyn std::error::Error>> {
        Ok(self.client.post(format!("{}/bulk-export/start", self.base_url))
            .json(&serde_json::json!({"project_id": project_id}))
            .send().await?.json().await?)
    }

    pub async fn get_bulk_export_status(&self, job_id: &str) -> Result<DiscoveryStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/bulk-export/status/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    pub async fn get_bulk_export_results(&self, job_id: &str) -> Result<BulkExportResult, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/bulk-export/results/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    // Drift
    pub async fn get_drift_prerequisites(&self) -> Result<DriftPrerequisites, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/drift/prerequisites", self.base_url))
            .send().await?.json().await?)
    }

    pub async fn start_drift(&self, tf_files: HashMap<String, String>, bucket: &str, prefix: &str, project_id: &str) -> Result<DriftJob, Box<dyn std::error::Error>> {
        Ok(self.client.post(format!("{}/drift/start", self.base_url))
            .json(&serde_json::json!({
                "tf_files": tf_files,
                "bucket": bucket,
                "prefix": prefix,
                "project_id": project_id,
            }))
            .send().await?.json().await?)
    }

    pub async fn get_drift_status(&self, job_id: &str) -> Result<DriftStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/drift/status/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    pub async fn get_drift_results(&self, job_id: &str) -> Result<DriftResults, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/drift/results/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    // AWS
    pub async fn get_aws_status(&self) -> Result<AIStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/settings/aws/status", self.base_url))
            .send().await?.json().await?)
    }

    pub async fn start_aws_discovery(&self, resource_types: &[String]) -> Result<DiscoveryJob, Box<dyn std::error::Error>> {
        Ok(self.client.post(format!("{}/aws/discovery/start", self.base_url))
            .json(&serde_json::json!({"resource_types": resource_types}))
            .send().await?.json().await?)
    }

    pub async fn get_aws_discovery_status(&self, job_id: &str) -> Result<DiscoveryStatus, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/aws/discovery/status/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }

    pub async fn get_aws_discovery_results(&self, job_id: &str) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        Ok(self.client.get(format!("{}/aws/discovery/results/{}", self.base_url, job_id))
            .send().await?.json().await?)
    }
}
