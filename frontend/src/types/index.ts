export type ScopeType = "project" | "folder" | "organization";

export type ResourceType =
  | "compute_instance"
  | "vpc_network"
  | "subnet"
  | "gcs_bucket"
  | "cloud_sql"
  | "gke_cluster"
  | "firewall_rule"
  | "load_balancer"
  | "cloud_run"
  | "cloud_function"
  | "pubsub_topic"
  | "pubsub_subscription"
  | "service_account"
  | "cloud_dns"
  | "memorystore_redis"
  | "iam_binding"
  | "custom_role"
  | "bigquery_dataset"
  | "secret"
  | "artifact_registry"
  | "kms_keyring"
  | "cloud_nat"
  | "cloud_scheduler"
  | "spanner_instance"
  | "filestore"
  | "cloud_armor"
  | "vpn_gateway"
  | "static_ip"
  | "cloud_tasks"
  | "dataflow_job"
  | "composer"
  | "api_gateway"
  | "logging_sink"
  | "monitoring_alert";

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
};

export const ALL_RESOURCE_TYPES: ResourceType[] = [
  "compute_instance",
  "vpc_network",
  "gcs_bucket",
  "cloud_sql",
  "gke_cluster",
  "firewall_rule",
  "load_balancer",
  "cloud_run",
  "cloud_function",
  "pubsub_topic",
  "service_account",
  "cloud_dns",
  "memorystore_redis",
  "iam_binding",
  "custom_role",
  "bigquery_dataset",
  "secret",
  "artifact_registry",
  "kms_keyring",
  "cloud_nat",
  "cloud_scheduler",
  "spanner_instance",
  "filestore",
  "cloud_armor",
  "vpn_gateway",
  "static_ip",
  "cloud_tasks",
  "dataflow_job",
  "composer",
  "api_gateway",
  "logging_sink",
  "monitoring_alert",
];
