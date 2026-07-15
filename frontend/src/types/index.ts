export type ScopeType = "project" | "folder" | "organization";

export type ResourceType =
  | "compute_instance"
  | "vpc_network"
  | "subnet"
  | "gcs_bucket"
  | "cloud_sql"
  | "gke_cluster";

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  compute_instance: "Compute Instances",
  vpc_network: "VPC Networks",
  subnet: "Subnets",
  gcs_bucket: "GCS Buckets",
  cloud_sql: "Cloud SQL",
  gke_cluster: "GKE Clusters",
};

export const ALL_RESOURCE_TYPES: ResourceType[] = [
  "compute_instance",
  "vpc_network",
  "gcs_bucket",
  "cloud_sql",
  "gke_cluster",
];
