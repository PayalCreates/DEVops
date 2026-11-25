output "ingress_class" {
  value = "traefik"
}

output "monitoring_enabled" {
  value = var.enable_monitoring
}

output "argocd_enabled" {
  value = var.enable_argocd
}
