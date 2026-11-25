output "namespace" {
  value = kubernetes_namespace_v1.app.metadata[0].name
}

output "admin_password" {
  description = "Bootstrap admin password (terraform output -raw admin_password)."
  value       = random_password.admin.result
  sensitive   = true
}

output "demo_user_password" {
  value     = var.seed_demo_users ? random_password.demo[0].result : null
  sensitive = true
}
