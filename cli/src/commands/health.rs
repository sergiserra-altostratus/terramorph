use colored::Colorize;

use crate::client::ApiClient;

pub async fn run(api: &ApiClient) -> Result<(), Box<dyn std::error::Error>> {
    let health = api.health().await?;
    let ai = api.ai_status().await.ok();
    let bulk = api.get_bulk_export_availability().await.ok();

    let api_status = if health.status == "ok" { "✓ Connected".green() } else { "✗ Error".red() };
    let gcp_status = if health.gcp_authenticated { "✓ Authenticated".green() } else { "✗ Not Authenticated".red() };
    let ai_status = match ai {
        Some(s) if s.configured => "✓ Configured".green(),
        _ => "✗ Not Configured".yellow(),
    };
    let bulk_status = match bulk {
        Some(b) if b.available => format!("✓ Available ({} types)", b.total_types).green(),
        _ => "✗ Not Available".yellow(),
    };

    println!("Terramorph Backend Status");
    println!("─────────────────────────");
    println!("  API:          {}", api_status);
    println!("  GCP:          {}", gcp_status);
    println!("  AI Cleaning:  {}", ai_status);
    println!("  Bulk Export:  {}", bulk_status);
    println!("  Version:      {}", health.version);

    Ok(())
}
