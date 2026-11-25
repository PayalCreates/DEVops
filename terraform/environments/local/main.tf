# LOCAL environment: kind cluster + add-ons + development namespace & secrets.
#
#   cd terraform/environments/local
#   terraform init
#   terraform apply            # ~3-5 min the first time (pulls node image)
#   terraform output -raw admin_password
#
# Then deploy the app: deployment/scripts/deploy-k8s.ps1 (or .sh)

terraform {
  required_version = ">= 1.6.0"

  # Local state is fine for a single-developer laptop environment.
  # It contains generated secrets: it is git-ignored — never commit it.
  backend "local" {
    path = "terraform.tfstate"
  }

  required_providers {
    kind       = { source = "tehcyx/kind", version = "~> 0.7" }
    helm       = { source = "hashicorp/helm", version = "~> 2.17" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.35" }
    random     = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

module "cluster" {
  source             = "../../modules/kind-cluster"
  cluster_name       = var.cluster_name
  kubernetes_version = var.kubernetes_version
  worker_count       = var.worker_count
  kubeconfig_path    = pathexpand("~/.kube/kind-${var.cluster_name}.yaml")
}

# Providers are configured from the cluster module's outputs, so a single
# `terraform apply` creates the cluster and then installs into it.
provider "helm" {
  kubernetes {
    host                   = module.cluster.endpoint
    client_certificate     = module.cluster.client_certificate
    client_key             = module.cluster.client_key
    cluster_ca_certificate = module.cluster.cluster_ca_certificate
  }
}

provider "kubernetes" {
  host                   = module.cluster.endpoint
  client_certificate     = module.cluster.client_certificate
  client_key             = module.cluster.client_key
  cluster_ca_certificate = module.cluster.cluster_ca_certificate
}

module "addons" {
  source                   = "../../modules/platform-addons"
  enable_monitoring        = var.enable_monitoring
  enable_argocd            = var.enable_argocd
  grafana_admin_password   = var.grafana_admin_password
  observability_values_dir = "${path.root}/../../../observability/kubernetes"
  depends_on               = [module.cluster]
}

module "app_dev" {
  source          = "../../modules/app-namespace"
  namespace       = "devsecops360-dev"
  environment     = "development"
  seed_demo_users = true
  depends_on      = [module.cluster]
}
