# PRODUCTION environment: same modules as staging (reproducibility), different inputs.
# No demo users, monitoring always on, Argo CD for GitOps.

terraform {
  required_version = ">= 1.6.0"
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
  enable_monitoring        = true
  enable_argocd            = true
  grafana_admin_password   = var.grafana_admin_password
  observability_values_dir = "${path.root}/../../../observability/kubernetes"
}

module "app" {
  source          = "../../modules/app-namespace"
  namespace       = "devsecops360-prod"
  environment     = "production"
  seed_demo_users = false
}

variable "kubeconfig_path" {
  type    = string
  default = "~/.kube/config"
}

variable "kube_context" {
  type = string
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}

output "namespace" {
  value = module.app.namespace
}
