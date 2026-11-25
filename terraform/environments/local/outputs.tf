output "kubectl_context" {
  value = module.cluster.context
}

output "kubeconfig_path" {
  value = module.cluster.kubeconfig_path
}

output "app_url" {
  value = "http://devsecops360.localtest.me:8088"
}

output "namespace" {
  value = module.app_dev.namespace
}

output "admin_password" {
  value     = module.app_dev.admin_password
  sensitive = true
}

output "demo_user_password" {
  value     = module.app_dev.demo_user_password
  sensitive = true
}
