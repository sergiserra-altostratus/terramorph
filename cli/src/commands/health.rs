use colored::Colorize;

use crate::client::ApiClient;

pub async fn run(api: &ApiClient) -> Result<(), Box<dyn std::error::Error>> {
    let health = api.health().await?;

    let api_status = if health.status == "ok" {
        "✓ Connected".green()
    } else {
        "✗ Error".red()
    };

    let gcp_status = if health.gcp_authenticated {
        "✓ Authenticated".green()
    } else {
        "✗ Not Authenticated".red()
    };

    println!("Terramorph Backend Status");
    println!("─────────────────────────");
    println!("  API:     {}", api_status);
    println!("  GCP:     {}", gcp_status);
    println!("  Version: {}", health.version);

    Ok(())
}
