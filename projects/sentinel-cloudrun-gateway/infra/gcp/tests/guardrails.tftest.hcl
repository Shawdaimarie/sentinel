mock_provider "google" {}
variables {
  image                     = "example.invalid/sentinel@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  runtime_environment       = {}
  project_id                = "sentinel-test-only"
  project_number            = "123456789"
  region                    = "us-central1"
  network                   = "private-test"
  subnetwork                = "private-test"
  database_secret_id        = "database"
  database_secret_version   = "1"
  capability_secret_id      = "capability"
  capability_secret_version = "1"
  artifact_bucket_name      = "sentinel-test-only-evidence"
  iap_members               = ["user:reviewer@example.invalid"]
}
run "private_bounded_staging_plan" {
  command = plan
  assert {
    condition     = google_cloud_run_v2_service.gateway.iap_enabled == true
    error_message = "IAP must protect the service"
  }
  assert {
    condition     = google_cloud_run_v2_service.gateway.template[0].scaling[0].max_instance_count == 2
    error_message = "Capacity must be bounded"
  }
  assert {
    condition     = google_storage_bucket.evidence.public_access_prevention == "enforced"
    error_message = "Artifacts cannot be public"
  }
  assert {
    condition     = local.runtime.SENTINEL_AUTH_MODE == "iap"
    error_message = "IAP auth is mandatory"
  }
}
run "reject_mutable_image" {
  command = plan
  variables { image = "example.invalid/sentinel:latest" }
  expect_failures = [var.image]
}
