variable "namespace" {
  description = "Kubernetes namespace (must match the Kustomize overlay)."
  type        = string
}

variable "environment" {
  description = "development | staging | production"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be development, staging or production."
  }
}

variable "seed_demo_users" {
  description = "Generate a password for the demo users (never in production)."
  type        = bool
  default     = false
}
