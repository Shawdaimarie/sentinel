terraform {
  required_version = "= 1.13.5"
  required_providers {
    kubernetes = { source = "hashicorp/kubernetes", version = "= 3.4.0" }
  }
}
# Workload configuration for an existing private Oracle Kubernetes Engine cluster.
# Cluster/Vault/CSI/IAM/database foundation must be verified separately before apply.
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kubeconfig_context
}
variable "kubeconfig_path" { type = string }
variable "kubeconfig_context" { type = string }
variable "namespace" { type = string }
variable "name" { default = "sentinel-staging" }
variable "image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "Use an immutable tested OCIR image digest."
  }
}
variable "image_pull_secret_name" { type = string }
variable "runtime_secret_name" { type = string }
variable "secret_provider_class" { type = string }
variable "runtime_environment" { type = map(string) }
resource "kubernetes_service_account_v1" "gateway" {
  metadata {
    name      = var.name
    namespace = var.namespace
  }
  automount_service_account_token = false
}
resource "kubernetes_deployment_v1" "gateway" {
  metadata {
    name      = var.name
    namespace = var.namespace
  }
  spec {
    replicas = 1
    selector { match_labels = { app = var.name } }
    template {
      metadata { labels = { app = var.name } }
      spec {
        service_account_name            = kubernetes_service_account_v1.gateway.metadata[0].name
        automount_service_account_token = false
        image_pull_secrets { name = var.image_pull_secret_name }
        security_context {
          run_as_non_root = true
          run_as_user     = 10001
          run_as_group    = 10001
          fs_group        = 10001
          seccomp_profile { type = "RuntimeDefault" }
        }
        container {
          name  = "gateway"
          image = var.image
          port { container_port = 8080 }
          dynamic "env" {
            for_each = local.runtime
            content {
              name  = env.key
              value = env.value
            }
          }
          dynamic "env" {
            for_each = toset(["DATABASE_URL", "CAPABILITY_SECRET"])
            content {
              name = env.value
              value_from {
                secret_key_ref {
                  name = var.runtime_secret_name
                  key  = env.value
                }
              }
            }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities { drop = ["ALL"] }
          }
          resources {
            requests = { cpu = "250m", memory = "256Mi" }
            limits   = { cpu = "1", memory = "512Mi" }
          }
          readiness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
          }
          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 60
          }
          volume_mount {
            name       = "vault"
            mount_path = "/mnt/secrets-store"
            read_only  = true
          }
          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "vault"
          csi {
            driver            = "secrets-store.csi.k8s.io"
            read_only         = true
            volume_attributes = { secretProviderClass = var.secret_provider_class }
          }
        }
        volume {
          name = "tmp"
          empty_dir { medium = "Memory" }
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "gateway" {
  metadata {
    name      = var.name
    namespace = var.namespace
  }
  spec {
    selector = { app = var.name }
    type     = "ClusterIP"
    port {
      port        = 8080
      target_port = 8080
    }
  }
}
output "internal_service" { value = "${var.name}.${var.namespace}.svc.cluster.local:8080" }

locals {
  runtime = merge(var.runtime_environment, { SENTINEL_ENVIRONMENT = "staging", SENTINEL_AUTH_MODE = "oidc", SENTINEL_LOCAL_TOKENS = "{}", PYTHONDONTWRITEBYTECODE = "1" })
}
