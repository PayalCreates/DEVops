variable "enable_monitoring" {
  description = "Install kube-prometheus-stack + Loki + Alloy (~1.5 GB RAM)."
  type        = bool
  default     = false
}

variable "enable_argocd" {
  description = "Install Argo CD for GitOps (~400 MB RAM)."
  type        = bool
  default     = false
}

variable "grafana_admin_password" {
  description = "Grafana admin password (only used when enable_monitoring = true)."
  type        = string
  sensitive   = true
  default     = ""
}

variable "observability_values_dir" {
  description = "Directory holding the Helm values files for the monitoring stack."
  type        = string
}

variable "traefik_chart_version" {
  type    = string
  default = "33.2.1"
}

variable "metrics_server_chart_version" {
  type    = string
  default = "3.12.2"
}

variable "kube_prometheus_stack_chart_version" {
  type    = string
  default = "67.9.0"
}

variable "loki_chart_version" {
  type    = string
  default = "6.24.0"
}

variable "alloy_chart_version" {
  type    = string
  default = "0.10.1"
}

variable "argocd_chart_version" {
  type    = string
  default = "7.7.11"
}
