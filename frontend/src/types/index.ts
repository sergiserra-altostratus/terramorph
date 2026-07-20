export type ScopeType = "project" | "folder" | "organization";

export type ResourceType =
  | "compute_instance" | "vpc_network" | "subnet" | "gcs_bucket" | "cloud_sql"
  | "gke_cluster" | "firewall_rule" | "load_balancer" | "cloud_run" | "cloud_function"
  | "pubsub_topic" | "pubsub_subscription" | "service_account" | "cloud_dns"
  | "memorystore_redis" | "iam_binding" | "custom_role" | "bigquery_dataset"
  | "secret" | "artifact_registry" | "kms_keyring" | "cloud_nat" | "cloud_scheduler"
  | "spanner_instance" | "filestore" | "cloud_armor" | "vpn_gateway" | "static_ip"
  | "cloud_tasks" | "dataflow_job" | "composer" | "api_gateway" | "logging_sink"
  | "monitoring_alert" | "ssl_policy" | "instance_group" | "bigtable_instance"
  | "compute_disk" | "vertex_ai_endpoint" | "compute_snapshot" | "instance_template"
  | "compute_image" | "compute_reservation" | "dns_policy" | "vpc_connector"
  | "compute_route" | "health_check";

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  compute_instance: "Compute Engine",
  vpc_network: "VPC Networks",
  subnet: "Subnets",
  gcs_bucket: "Cloud Storage",
  cloud_sql: "Cloud SQL",
  gke_cluster: "GKE Clusters",
  firewall_rule: "Firewall Rules",
  load_balancer: "Load Balancers",
  cloud_run: "Cloud Run",
  cloud_function: "Cloud Functions",
  pubsub_topic: "Pub/Sub Topics",
  pubsub_subscription: "Pub/Sub Subs",
  service_account: "Service Accounts",
  cloud_dns: "Cloud DNS",
  memorystore_redis: "Memorystore",
  iam_binding: "IAM Bindings",
  custom_role: "Custom Roles",
  bigquery_dataset: "BigQuery",
  secret: "Secret Manager",
  artifact_registry: "Artifact Registry",
  kms_keyring: "Cloud KMS",
  cloud_nat: "Cloud NAT",
  cloud_scheduler: "Cloud Scheduler",
  spanner_instance: "Cloud Spanner",
  filestore: "Filestore",
  cloud_armor: "Cloud Armor",
  vpn_gateway: "VPN Gateway",
  static_ip: "Static IPs",
  cloud_tasks: "Cloud Tasks",
  dataflow_job: "Dataflow",
  composer: "Composer",
  api_gateway: "API Gateway",
  logging_sink: "Logging Sinks",
  monitoring_alert: "Monitoring Alerts",
  ssl_policy: "SSL Policies",
  instance_group: "Instance Groups",
  bigtable_instance: "Bigtable",
  compute_disk: "Persistent Disks",
  vertex_ai_endpoint: "Vertex AI",
  compute_snapshot: "Snapshots",
  instance_template: "Instance Templates",
  compute_image: "Compute Images",
  compute_reservation: "Reservations",
  dns_policy: "DNS Policies",
  vpc_connector: "VPC Connectors",
  compute_route: "Routes",
  health_check: "Health Checks",
};

/** Resource types grouped by category for better UI organization */
export const RESOURCE_CATEGORIES: Record<string, ResourceType[]> = {
  "Compute": ["compute_instance", "compute_disk", "compute_image", "compute_snapshot", "instance_template", "instance_group", "compute_reservation", "static_ip"],
  "Networking": ["vpc_network", "firewall_rule", "load_balancer", "cloud_nat", "vpn_gateway", "compute_route", "health_check", "ssl_policy", "dns_policy", "vpc_connector", "cloud_dns"],
  "Containers & Serverless": ["gke_cluster", "cloud_run", "cloud_function", "cloud_scheduler", "cloud_tasks"],
  "Storage & Databases": ["gcs_bucket", "cloud_sql", "spanner_instance", "bigquery_dataset", "memorystore_redis", "bigtable_instance", "filestore"],
  "Security & IAM": ["service_account", "iam_binding", "custom_role", "cloud_armor", "secret", "kms_keyring"],
  "Messaging & Integration": ["pubsub_topic", "pubsub_subscription", "api_gateway"],
  "Data & AI": ["dataflow_job", "vertex_ai_endpoint", "composer"],
  "Observability": ["logging_sink", "monitoring_alert"],
  "CI/CD": ["artifact_registry"],
};

export const ALL_RESOURCE_TYPES: ResourceType[] = Object.values(RESOURCE_CATEGORIES).flat();
