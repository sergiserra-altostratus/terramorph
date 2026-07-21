use clap::{Parser, Subcommand, ValueEnum};

mod commands;
mod client;
mod output;

#[derive(Parser)]
#[command(name = "terramorph")]
#[command(about = "Terramorph CLI - Reverse Terraform for GCP")]
#[command(version = "0.1.0")]
struct Cli {
    /// Backend API URL
    #[arg(long, default_value = "http://localhost:8001/api/v1", env = "TERRAMORPH_API_URL")]
    api_url: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Clone, ValueEnum)]
enum CloudProvider {
    Gcp,
    Aws,
}

#[derive(Clone, ValueEnum)]
enum DiscoveryMode {
    Api,
    BulkExport,
}

#[derive(Clone, ValueEnum)]
enum GenerationStyle {
    Flat,
    Module,
}

#[derive(Subcommand)]
enum Commands {
    /// Discover GCP resources
    Discover {
        /// Cloud provider to scan
        #[arg(long, value_enum, default_value = "gcp")]
        provider: CloudProvider,

        /// GCP Project ID (GCP only)
        #[arg(long, group = "scope")]
        project: Option<String>,

        /// GCP Folder ID (GCP only)
        #[arg(long, group = "scope")]
        folder: Option<String>,

        /// GCP Organization ID (GCP only)
        #[arg(long, group = "scope")]
        organization: Option<String>,

        /// Discovery mode: api (fast, parallel) or bulk-export (precise, uses gcloud). GCP only.
        #[arg(long, value_enum, default_value = "api")]
        mode: DiscoveryMode,

        /// Resource types to discover (comma-separated). Use 'all' for all supported types.
        #[arg(long, default_value = "all")]
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

        /// Generation style: flat (resource blocks) or module (official Google modules)
        #[arg(long, value_enum, default_value = "flat")]
        style: GenerationStyle,

        /// Enable AI code cleaning (requires AI configured in Settings)
        #[arg(long)]
        ai_clean: bool,

        /// GCS bucket name for remote state (generates backend.tf)
        #[arg(long)]
        state_bucket: Option<String>,

        /// Path prefix for state file within the bucket
        #[arg(long, default_value = "terraform/state")]
        state_prefix: Option<String>,
    },

    /// Run drift detection and AI auto-fix
    Drift {
        /// Path to directory containing .tf files to check
        #[arg(long, short)]
        path: String,

        /// GCS bucket for remote state (required)
        #[arg(long)]
        bucket: String,

        /// State prefix in the bucket
        #[arg(long, default_value = "terraform/state")]
        prefix: String,

        /// GCP project ID
        #[arg(long)]
        project: String,
    },

    /// Check discovery job status
    Status {
        /// Job ID to check
        #[arg(long)]
        job_id: String,
    },

    /// Check backend health and configuration
    Health,
}

#[tokio::main]
async fn main() {
    let cli = Cli::parse();
    let api = client::ApiClient::new(&cli.api_url);

    let result = match cli.command {
        Commands::Discover { provider, project, folder, organization, mode, types } => {
            commands::discover::run(&api, provider, project, folder, organization, &types, mode).await
        }
        Commands::Generate { job_id, output, style, ai_clean, state_bucket, state_prefix } => {
            commands::generate::run(&api, &job_id, &output, style, ai_clean, state_bucket, state_prefix).await
        }
        Commands::Drift { path, bucket, prefix, project } => {
            commands::drift::run(&api, &path, &bucket, &prefix, &project).await
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
