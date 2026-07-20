use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::time::Duration;
use tabled::{Table, Tabled};

use crate::client::ApiClient;
use crate::DiscoveryMode;

#[derive(Tabled)]
struct ResourceRow {
    #[tabled(rename = "Name")]
    name: String,
    #[tabled(rename = "Type")]
    resource_type: String,
    #[tabled(rename = "Project")]
    project: String,
    #[tabled(rename = "Location")]
    location: String,
}

pub async fn run(
    api: &ApiClient,
    project: Option<String>,
    folder: Option<String>,
    organization: Option<String>,
    types: &str,
    mode: DiscoveryMode,
) -> Result<(), Box<dyn std::error::Error>> {
    let (scope_type, scope_id) = if let Some(p) = project {
        ("project".to_string(), p)
    } else if let Some(f) = folder {
        ("folder".to_string(), f)
    } else if let Some(o) = organization {
        ("organization".to_string(), o)
    } else {
        return Err("Must specify --project, --folder, or --organization".into());
    };

    match mode {
        DiscoveryMode::Api => run_api_discovery(api, &scope_type, &scope_id, types).await,
        DiscoveryMode::BulkExport => run_bulk_export(api, &scope_id).await,
    }
}

async fn run_api_discovery(
    api: &ApiClient,
    scope_type: &str,
    scope_id: &str,
    types: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let resource_types: Vec<String> = if types == "all" {
        vec![] // Empty means all in the API
    } else {
        types.split(',').map(|s| s.trim().to_string()).collect()
    };

    println!("{} Starting API discovery for {} {}...",
        "●".green(), scope_type, scope_id.bold()
    );

    let job = api.start_discovery(scope_type, scope_id, &resource_types).await?;
    println!("{} Job ID: {}", "●".blue(), job.job_id);

    let pb = ProgressBar::new(100);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40.cyan/blue}] {msg}")
            .unwrap()
            .progress_chars("█▓░"),
    );

    loop {
        tokio::time::sleep(Duration::from_secs(2)).await;
        let status = api.get_discovery_status(&job.job_id).await?;

        let pct = if status.progress.total > 0 {
            (status.progress.completed as u64 * 100) / status.progress.total as u64
        } else { 0 };
        pb.set_position(pct);
        pb.set_message(status.progress.message.clone());

        match status.status.as_str() {
            "completed" => { pb.finish_with_message("Discovery complete!"); break; }
            "failed" => {
                pb.finish_with_message("Discovery failed!");
                return Err(status.error.unwrap_or("Unknown error".to_string()).into());
            }
            _ => {}
        }
    }

    let results = api.get_discovery_results(&job.job_id).await?;
    println!("\n{} Found {} resources:\n", "✓".green().bold(), results.resources.len().to_string().bold());

    let rows: Vec<ResourceRow> = results.resources.iter().map(|r| ResourceRow {
        name: r.name.clone(),
        resource_type: r.terraform_resource_type.clone(),
        project: r.project.clone(),
        location: r.location.clone(),
    }).collect();

    if !rows.is_empty() {
        let table = Table::new(rows).to_string();
        println!("{}", table);
    }

    println!("\n{} To generate Terraform code, run:", "→".blue());
    println!("  terramorph generate --job-id {}", job.job_id);

    Ok(())
}

async fn run_bulk_export(
    api: &ApiClient,
    project_id: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("{} Starting Bulk Export for project {}...", "●".green(), project_id.bold());
    println!("{} Mode: Bulk Export (precise, uses gcloud Cloud Asset API)", "●".blue());

    // Check availability
    let avail = api.get_bulk_export_availability().await?;
    if !avail.available {
        return Err("gcloud CLI not available in the backend. Bulk Export requires Google Cloud SDK.".into());
    }

    // Check Cloud Asset API
    print!("{} Checking Cloud Asset API... ", "●".blue());
    let api_check = api.check_cloud_asset_api(project_id).await?;
    if !api_check.enabled {
        println!("{}", "NOT ENABLED".red());
        println!("  {}", api_check.message.unwrap_or_default());
        return Err("Cloud Asset API is not enabled for this project.".into());
    }
    println!("{}", "ENABLED".green());

    // Start bulk export
    let job = api.start_bulk_export(project_id).await?;
    println!("{} Job ID: {}", "●".blue(), job.job_id);

    let pb = ProgressBar::new(100);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40.cyan/blue}] {msg}")
            .unwrap()
            .progress_chars("█▓░"),
    );

    loop {
        tokio::time::sleep(Duration::from_secs(3)).await;
        let status = api.get_bulk_export_status(&job.job_id).await?;

        let pct = if status.progress.total > 0 {
            (status.progress.completed as u64 * 100) / status.progress.total as u64
        } else { 0 };
        pb.set_position(pct);
        pb.set_message(status.progress.message.clone());

        match status.status.as_str() {
            "completed" => { pb.finish_with_message("Bulk export complete!"); break; }
            "failed" => {
                pb.finish_with_message("Bulk export failed!");
                return Err(status.error.unwrap_or("Unknown error".to_string()).into());
            }
            _ => {}
        }
    }

    let results = api.get_bulk_export_results(&job.job_id).await?;
    let file_count = results.tf_files.len();
    let resource_count = results.resources.len();

    println!("\n{} Exported {} resources across {} files\n", "✓".green().bold(), resource_count, file_count);

    for (filename, _content) in &results.tf_files {
        println!("  {} {}", "✓".green(), filename);
    }

    println!("\n{} Bulk export results are stored in job: {}", "→".blue(), job.job_id);

    Ok(())
}
