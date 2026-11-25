# STAGING environment: targets an EXISTING cluster (any conformant Kubernetes:
# a second kind cluster, a lab server, or a cloud cluster) via a kubeconfig context.
# Cloud provisioning is intentionally optional for this project.
#
#   terraform init -backend-config=backend.hcl   # remote state, see backend.hcl.example
#   terraform apply -var kube_context=<context>

terraform {
  required_version = ">= 1.6.0"

  # Shared environments need shared, locked state. Example uses an S3-compatible
  # bucket (works with MinIO for a fully local setup). Values come from backend.hcl.
  backend "s3" {}

  required_providers {
    helm       = { source = "hashicorp/helm", version = "~> 2.17" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.35" }
    random     = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

module "addons" {
  source                   = "../../modules/platform-addons"
  enable_monitoring        = var.enable_monitoring
  enable_argocd            = true
  grafana_admin_password   = var.grafana_admin_password
  observability_values_dir = "${path.root}/../../../observability/kubernetes"
}

module "app" {
  source          = "../../modules/app-namespace"
  namespace       = "devsecops360-staging"
  environment     = "staging"
  seed_demo_users = true
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}

variable "kube_context" {
  type = string
}

variable "enable_monitoring" {
  type    = bool
  default = true
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}

output "namespace" {
  value = module.app.namespace
}
