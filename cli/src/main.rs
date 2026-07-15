use clap::{Parser, Subcommand};

mod commands;
mod client;
mod output;

#[derive(Parser)]
#[command(name = "terramorph")]
#[command(about = "Terramorph CLI - Reverse Terraform for GCP")]
#[command(version = "0.1.0")]
struct Cli {
    /// Backend API URL
    #[arg(long, default_value = "http://localhost:8000/api/v1", env = "TERRAMORPH_API_URL")]
    api_url: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Discover GCP resources
    Discover {
        /// GCP Project ID
        #[arg(long, group = "scope")]
        project: Option<String>,

        /// GCP Folder ID
        #[arg(long, group = "scope")]
        folder: Option<String>,

        /// GCP Organization ID
        #[arg(long, group = "scope")]
        organization: Option<String>,

        /// Resource types to discover (comma-separated)
        #[arg(long, default_value = "compute_instance,vpc_network,gcs_bucket,cloud_sql,gke_cluster")]
        types: String,
    },

    /// Generate Terraform code from discovery results
    Generate {
        /// Job ID from a previous discovery
        #[arg(long)]
        job_id: String,

        /// Output directory for generated files
        #[arg(long, short, default_value = "./terraform")]
        output: String,

        /// GCS bucket name for remote state (generates backend.tf)
        #[arg(long)]
        state_bucket: Option<String>,

        /// Path prefix for state file within the bucket
        #[arg(long, default_value = "terraform/state")]
        state_prefix: Option<String>,
    },

    /// Check discovery job status
    Status {
        /// Job ID to check
        #[arg(long)]
        job_id: String,
    },

    /// Check backend health
    Health,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let api = client::ApiClient::new(&cli.api_url);

    let result = match cli.command {
        Commands::Discover { project, folder, organization, types } => {
            commands::discover::run(&api, project, folder, organization, &types).await
        }
        Commands::Generate { job_id, output, state_bucket, state_prefix } => {
            commands::generate::run(&api, &job_id, &output, state_bucket, state_prefix).await
        }
        Commands::Status { job_id } => {
            commands::status::run(&api, &job_id).await
        }
        Commands::Health => {
            commands::health::run(&api).await
        }
    };

    if let Err(e) = result {
        eprintln!("\x1b[31merror:\x1b[0m {}", e);
        std::process::exit(1);
    }
}
