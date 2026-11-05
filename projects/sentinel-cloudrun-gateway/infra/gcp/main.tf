terraform {
  required_version = "= 1.13.5"
  required_providers {
    google = { source = "hashicorp/google", version = "= 8.9.0" }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
variable "project_id" { type = string }
variable "project_number" { type = string }
variable "region" { type = string }
variable "name" { default = "sentinel-staging" }
variable "image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "Use an immutable, tested container image digest."
  }
}
variable "network" { type = string }
variable "subnetwork" { type = string }
variable "database_secret_id" { type = string }
variable "database_secret_version" { type = string }
variable "capability_secret_id" { type = string }
variable "capability_secret_version" { type = string }
variable "artifact_bucket_name" { type = string }
variable "runtime_environment" {
  type        = map(string)
  description = "Non-secret production OIDC/environment configuration; must match the tested app config contract."
}
variable "iap_members" {
  type = set(string)
  validation {
    condition     = length(var.iap_members) > 0 && !contains(var.iap_members, "allUsers") && !contains(var.iap_members, "allAuthenticatedUsers")
    error_message = "Staging invocation requires explicit authenticated principals."
  }
}
resource "google_service_account" "runtime" {
  account_id   = var.name
  display_name = "SENTINEL staging runtime"
}
resource "google_secret_manager_secret_iam_member" "read" {
  for_each  = toset([var.database_secret_id, var.capability_secret_id])
  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_storage_bucket" "evidence" {
  name                        = var.artifact_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning { enabled = true }
  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}
resource "google_storage_bucket_iam_member" "writer" {
  bucket = google_storage_bucket.evidence.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_cloud_run_v2_service" "gateway" {
  name                = var.name
  location            = var.region
  deletion_protection = true
  # Direct IAP protects browser access on the Cloud Run URL; DB egress stays private.
  ingress     = "INGRESS_TRAFFIC_ALL"
  iap_enabled = true
  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "30s"
    max_instance_request_concurrency = 10
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = var.network
        subnetwork = var.subnetwork
      }
    }
    containers {
      image = var.image
      ports { container_port = 8080 }
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
      dynamic "env" {
        for_each = local.runtime
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = var.database_secret_id
            version = var.database_secret_version
          }
        }
      }
      env {
        name = "CAPABILITY_SECRET"
        value_source {
          secret_key_ref {
            secret  = var.capability_secret_id
            version = var.capability_secret_version
          }
        }
      }
      startup_probe {
        http_get { path = "/health" }
        period_seconds    = 5
        failure_threshold = 12
      }
      liveness_probe {
        http_get { path = "/health" }
        period_seconds = 30
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.read]
}
resource "google_cloud_run_v2_service_iam_member" "invoke" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.gateway.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${var.project_number}@gcp-sa-iap.iam.gserviceaccount.com"
}
resource "google_iap_web_cloud_run_service_iam_member" "reviewer" {
  for_each               = var.iap_members
  project                = var.project_id
  location               = var.region
  cloud_run_service_name = google_cloud_run_v2_service.gateway.name
  role                   = "roles/iap.httpsResourceAccessor"
  member                 = each.value
}
output "gateway_uri" { value = google_cloud_run_v2_service.gateway.uri }
output "runtime_service_account" { value = google_service_account.runtime.email }
output "evidence_bucket" { value = google_storage_bucket.evidence.name }

locals {
  runtime = merge(var.runtime_environment, { SENTINEL_ENVIRONMENT = "staging", SENTINEL_AUTH_MODE = "iap", SENTINEL_LOCAL_TOKENS = "{}", PYTHONDONTWRITEBYTECODE = "1", SENTINEL_IAP_AUDIENCE = "/projects/${var.project_number}/locations/${var.region}/services/${var.name}" })
}
