use colored::Colorize;

use crate::client::ApiClient;

pub async fn run(api: &ApiClient, job_id: &str) -> Result<(), Box<dyn std::error::Error>> {
    let status = api.get_status(job_id).await?;

    let status_icon = match status.status.as_str() {
        "completed" => "✓".green(),
        "failed" => "✗".red(),
        "running" => "●".yellow(),
        _ => "○".white(),
    };

    println!("{} Job: {}", status_icon, job_id);
    println!("  Status: {}", status.status);
    println!(
        "  Progress: {}/{}",
        status.progress.completed, status.progress.total
    );
    println!("  Resources found: {}", status.resources_found);
    println!("  Message: {}", status.progress.message);

    if let Some(err) = status.error {
        println!("  Error: {}", err.red());
    }

    Ok(())
}
