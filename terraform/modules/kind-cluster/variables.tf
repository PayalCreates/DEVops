variable "cluster_name" {
  description = "Name of the kind cluster (also the kubectl context suffix: kind-<name>)."
  type        = string
  default     = "devsecops360"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,40}$", var.cluster_name))
    error_message = "cluster_name must be 3-40 lowercase letters, digits or dashes."
  }
}

variable "kubernetes_version" {
  description = "kindest/node image tag (Kubernetes version)."
  type        = string
  default     = "v1.31.4"
}

variable "worker_count" {
  description = "Extra worker nodes. Keep 0 on an 8 GB laptop."
  type        = number
  default     = 0

  validation {
    condition     = var.worker_count >= 0 && var.worker_count <= 3
    error_message = "worker_count must be between 0 and 3."
  }
}

variable "http_host_port" {
  description = "Laptop port mapped to the ingress HTTP NodePort."
  type        = number
  default     = 8088
}

variable "https_host_port" {
  description = "Laptop port mapped to the ingress HTTPS NodePort."
  type        = number
  default     = 8443
}

variable "kubeconfig_path" {
  description = "Where kind writes the kubeconfig for this cluster."
  type        = string
}
