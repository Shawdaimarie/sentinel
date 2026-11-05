terraform {
  required_version = "= 1.13.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "= 5.12.0" }
  }
}
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "name" { default = "sentinel-staging" }
variable "container_app_environment_id" { type = string }
variable "key_vault_id" { type = string }
variable "database_secret_url" { type = string }
variable "capability_secret_url" { type = string }
variable "registry_server" { type = string }
variable "registry_id" { type = string }
variable "image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "Use an immutable tested ACR image digest."
  }
}
variable "runtime_environment" { type = map(string) }
resource "azurerm_user_assigned_identity" "runtime" {
  name                = "${var.name}-runtime"
  resource_group_name = var.resource_group_name
  location            = var.location
}
resource "azurerm_role_assignment" "secrets" {
  scope                = var.key_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.runtime.principal_id
}
resource "azurerm_role_assignment" "registry" {
  scope                = var.registry_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.runtime.principal_id
}
resource "azurerm_container_app" "gateway" {
  name                         = var.name
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.runtime.id]
  }
  registry {
    server   = var.registry_server
    identity = azurerm_user_assigned_identity.runtime.id
  }
  secret {
    name                = "database-url"
    identity            = azurerm_user_assigned_identity.runtime.id
    key_vault_secret_id = var.database_secret_url
  }
  secret {
    name                = "capability-secret"
    identity            = azurerm_user_assigned_identity.runtime.id
    key_vault_secret_id = var.capability_secret_url
  }
  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8080
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
  template {
    min_replicas = 0
    max_replicas = 2
    container {
      name   = "gateway"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"
      dynamic "env" {
        for_each = local.runtime
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "CAPABILITY_SECRET"
        secret_name = "capability-secret"
      }
      readiness_probe {
        transport = "HTTP"
        port      = 8080
        path      = "/health"
      }
      liveness_probe {
        transport = "HTTP"
        port      = 8080
        path      = "/health"
      }
    }
  }
  depends_on = [azurerm_role_assignment.secrets, azurerm_role_assignment.registry]
}
output "gateway_fqdn" { value = azurerm_container_app.gateway.latest_revision_fqdn }
output "runtime_identity" { value = azurerm_user_assigned_identity.runtime.id }

locals {
  runtime = merge(var.runtime_environment, { SENTINEL_ENVIRONMENT = "staging", SENTINEL_AUTH_MODE = "oidc", SENTINEL_LOCAL_TOKENS = "{}", PYTHONDONTWRITEBYTECODE = "1" })
}
