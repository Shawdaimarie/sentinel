mock_provider "kubernetes" {}
variables {
  image                  = "example.invalid/sentinel@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  runtime_environment    = {}
  kubeconfig_path        = "/tmp/nonexistent-test-kubeconfig"
  kubeconfig_context     = "oke-test-only"
  namespace              = "sentinel"
  image_pull_secret_name = "ocir-pull"
  runtime_secret_name    = "sentinel-runtime"
  secret_provider_class  = "sentinel-vault"
}
run "private_bounded_staging_plan" {
  command = plan
  assert {
    condition     = kubernetes_service_v1.gateway.spec[0].type == "ClusterIP"
    error_message = "No public service"
  }
  assert {
    condition     = kubernetes_deployment_v1.gateway.spec[0].template[0].spec[0].automount_service_account_token == false
    error_message = "Do not expose cluster API tokens"
  }
  assert {
    condition     = kubernetes_deployment_v1.gateway.spec[0].template[0].spec[0].container[0].security_context[0].read_only_root_filesystem == true
    error_message = "Filesystem must be read-only"
  }
  assert {
    condition     = local.runtime.SENTINEL_AUTH_MODE == "oidc"
    error_message = "OIDC required"
  }
}
run "reject_mutable_image" {
  command = plan
  variables { image = "example.invalid/sentinel:latest" }
  expect_failures = [var.image]
}
