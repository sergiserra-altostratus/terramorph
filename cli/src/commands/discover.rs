use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::time::Duration;
use tabled::{Table, Tabled};

use crate::client::{ApiClient, DiscoveryRequest, Scope};

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

    let resource_types: Vec<String> = types.split(',').map(|s| s.trim().to_string()).collect();

    println!("{} Starting discovery for {} {}...",
        "●".green(),
        scope_type,
        scope_id.bold()
    );

    let req = DiscoveryRequest {
        scope: Scope { scope_type, id: scope_id },
        resource_types,
    };

    let job = api.start_discovery(&req).await?;
    println!("{} Job ID: {}", "●".blue(), job.job_id);

    // Poll with progress bar
    let pb = ProgressBar::new(100);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40.cyan/blue}] {msg}")
            .unwrap()
            .progress_chars("█▓░"),
    );

    loop {
        tokio::time::sleep(Duration::from_secs(2)).await;
        let status = api.get_status(&job.job_id).await?;

        let pct = if status.progress.total > 0 {
            (status.progress.completed as u64 * 100) / status.progress.total as u64
        } else {
            0
        };
        pb.set_position(pct);
        pb.set_message(status.progress.message.clone());

        match status.status.as_str() {
            "completed" => {
                pb.finish_with_message("Discovery complete!");
                break;
            }
            "failed" => {
                pb.finish_with_message("Discovery failed!");
                return Err(status.error.unwrap_or("Unknown error".to_string()).into());
            }
            _ => {}
        }
    }

    // Fetch and display results
    let results = api.get_results(&job.job_id).await?;

    println!("\n{} Found {} resources:\n",
        "✓".green().bold(),
        results.resources.len().to_string().bold()
    );

    let rows: Vec<ResourceRow> = results.resources.iter().map(|r| ResourceRow {
        name: r.name.clone(),
        resource_type: r.terraform_resource_type.clone(),
        project: r.project.clone(),
        location: r.location.clone(),
    }).collect();

    let table = Table::new(rows).to_string();
    println!("{}", table);

    println!("\n{} To generate Terraform code, run:", "→".blue());
    println!("  terramorph generate --job-id {}", job.job_id);

    Ok(())
}
