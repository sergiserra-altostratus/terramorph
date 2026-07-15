use colored::Colorize;
use std::fs;
use std::path::Path;

use crate::client::{ApiClient, BackendStateConfig, GenerationOptions, GenerationRequest};

pub async fn run(
    api: &ApiClient,
    job_id: &str,
    output: &str,
    state_bucket: Option<String>,
    state_prefix: Option<String>,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("{} Generating Terraform code for job {}...", "●".green(), job_id);

    let backend_state = state_bucket.map(|bucket| BackendStateConfig {
        bucket,
        prefix: state_prefix.unwrap_or_else(|| "terraform/state".to_string()),
    });

    let req = GenerationRequest {
        job_id: job_id.to_string(),
        resource_ids: vec!["all".to_string()],
        options: GenerationOptions {
            include_provider_block: true,
            include_import_script: true,
            output_format: "per_resource_type".to_string(),
            backend_state,
        },
    };

    let result = api.generate(&req).await?;

    // Create output directory
    let output_path = Path::new(output);
    fs::create_dir_all(output_path)?;

    // Write files
    for file in &result.files {
        let file_path = output_path.join(&file.filename);
        fs::write(&file_path, &file.content)?;
        println!("  {} {}", "✓".green(), file_path.display());
    }

    println!(
        "\n{} Generated {} files ({} resources, {} import commands)",
        "✓".green().bold(),
        result.files.len(),
        result.total_resources,
        result.import_commands
    );

    println!("\n{} Next steps:", "→".blue());
    println!("  1. cd {}", output);
    println!("  2. terraform init");
    println!("  3. bash import.sh");
    println!("  4. terraform plan");

    Ok(())
}
