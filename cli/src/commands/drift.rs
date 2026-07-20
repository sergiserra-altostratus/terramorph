use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::time::Duration;

use crate::client::ApiClient;

pub async fn run(
    api: &ApiClient,
    path: &str,
    bucket: &str,
    prefix: &str,
    project: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("{} Starting drift detection...", "●".green());
    println!("  Path:    {}", path);
    println!("  Bucket:  {}", bucket);
    println!("  Prefix:  {}", prefix);
    println!("  Project: {}", project);

    // Check prerequisites
    let prereqs = api.get_drift_prerequisites().await?;
    if !prereqs.ready {
        println!("\n{} Prerequisites not met:", "✗".red());
        for msg in &prereqs.missing {
            println!("  • {}", msg);
        }
        return Err("Configure an AI provider in Settings before using drift detection.".into());
    }
    println!("  AI:      {} ({})", "ready".green(), prereqs.ai_provider.unwrap_or_default());

    // Read .tf files from path
    let dir_path = Path::new(path);
    if !dir_path.is_dir() {
        return Err(format!("'{}' is not a directory", path).into());
    }

    let mut tf_files: HashMap<String, String> = HashMap::new();
    for entry in fs::read_dir(dir_path)? {
        let entry = entry?;
        let file_path = entry.path();
        if file_path.extension().and_then(|e| e.to_str()) == Some("tf") {
            let filename = file_path.file_name().unwrap().to_str().unwrap().to_string();
            let content = fs::read_to_string(&file_path)?;
            tf_files.insert(filename, content);
        }
    }

    if tf_files.is_empty() {
        return Err(format!("No .tf files found in '{}'", path).into());
    }

    println!("\n{} Found {} .tf files, starting drift analysis...\n", "●".blue(), tf_files.len());

    // Start drift detection
    let job = api.start_drift(tf_files, bucket, prefix, project).await?;

    let pb = ProgressBar::new(10);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40.cyan/blue}] {msg}")
            .unwrap()
            .progress_chars("█▓░"),
    );

    loop {
        tokio::time::sleep(Duration::from_secs(3)).await;
        let status = api.get_drift_status(&job.job_id).await?;

        pb.set_position(status.progress.iteration as u64);
        pb.set_message(status.progress.message.clone());

        match status.status.as_str() {
            "completed" => { pb.finish_with_message("Done!"); break; }
            "failed" => {
                pb.finish_with_message("Failed!");
                return Err(status.error.unwrap_or("Drift detection failed".to_string()).into());
            }
            _ => {}
        }
    }

    // Get results
    let results = api.get_drift_results(&job.job_id).await?;

    if let Some(result) = results.result {
        println!("\n{} {}", "✓".green().bold(), result.message);

        if let Some(iterations) = result.iterations_needed {
            if iterations > 0 {
                println!("  Fixed in {} iteration(s)", iterations);
            }
        }

        // Write corrected files back
        if let Some(final_files) = result.final_files {
            println!("\n{} Updated files:", "→".blue());
            for (filename, content) in &final_files {
                let file_path = dir_path.join(filename);
                fs::write(&file_path, content)?;
                println!("  {} {}", "✓".green(), file_path.display());
            }
        }
    }

    Ok(())
}
