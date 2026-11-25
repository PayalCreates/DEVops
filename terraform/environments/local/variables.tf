variable "cluster_name" {
  type    = string
  default = "devsecops360"
}

variable "kubernetes_version" {
  type    = string
  default = "v1.31.4"
}

variable "worker_count" {
  type    = number
  default = 0
}

variable "enable_monitoring" {
  description = "Prometheus/Grafana/Loki inside the cluster. Needs ~1.5 GB extra RAM."
  type        = bool
  default     = false
}

variable "enable_argocd" {
  type    = bool
  default = false
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
  default   = ""

  validation {
    condition     = var.grafana_admin_password == "" || length(var.grafana_admin_password) >= 12
    error_message = "grafana_admin_password must be at least 12 characters."
  }
}
