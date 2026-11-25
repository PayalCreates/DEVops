# Cluster add-ons installed with Helm. Heavy components are OFF by default so the
# platform fits in 8 GB RAM; switch them on only when you demo them.

resource "helm_release" "traefik" {
  name             = "traefik"
  repository       = "https://traefik.github.io/charts"
  chart            = "traefik"
  version          = var.traefik_chart_version
  namespace        = "traefik"
  create_namespace = true
  wait             = true
  timeout          = 300

  values = [yamlencode({
    deployment   = { replicas = 1 }
    ingressClass = { enabled = true, isDefaultClass = true, name = "traefik" }
    providers = {
      kubernetesCRD     = { enabled = true, allowCrossNamespace = false }
      kubernetesIngress = { enabled = true }
    }
    service = { type = "NodePort" }
    ports = {
      web       = { nodePort = 30080 }
      websecure = { nodePort = 30443 }
    }
    nodeSelector = { "ingress-ready" = "true" }
    tolerations = [{
      key      = "node-role.kubernetes.io/control-plane"
      operator = "Exists"
      effect   = "NoSchedule"
    }]
    resources = {
      requests = { cpu = "50m", memory = "64Mi" }
      limits   = { cpu = "300m", memory = "128Mi" }
    }
    logs    = { access = { enabled = true, format = "json" } }
    metrics = { prometheus = { serviceMonitor = { enabled = var.enable_monitoring } } }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true

  values = [yamlencode({
    # kind kubelets use self-signed certs
    args      = ["--kubelet-insecure-tls"]
    resources = { requests = { cpu = "20m", memory = "48Mi" } }
  })]
}

# ---------------------------------------------------------------- monitoring
resource "helm_release" "kube_prometheus_stack" {
  count            = var.enable_monitoring ? 1 : 0
  name             = "monitoring"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = var.kube_prometheus_stack_chart_version
  namespace        = "monitoring"
  create_namespace = true
  timeout          = 600

  values = [file("${var.observability_values_dir}/kube-prometheus-stack.values.yaml")]

  set_sensitive {
    name  = "grafana.adminPassword"
    value = var.grafana_admin_password
  }
}

resource "helm_release" "loki" {
  count      = var.enable_monitoring ? 1 : 0
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  version    = var.loki_chart_version
  namespace  = "monitoring"
  timeout    = 600
  values     = [file("${var.observability_values_dir}/loki.values.yaml")]
  depends_on = [helm_release.kube_prometheus_stack]
}

resource "helm_release" "alloy" {
  count      = var.enable_monitoring ? 1 : 0
  name       = "alloy"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "alloy"
  version    = var.alloy_chart_version
  namespace  = "monitoring"
  values     = [file("${var.observability_values_dir}/alloy.values.yaml")]
  depends_on = [helm_release.loki]
}

# --------------------------------------------------------------------- GitOps
resource "helm_release" "argocd" {
  count            = var.enable_argocd ? 1 : 0
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version
  namespace        = "argocd"
  create_namespace = true
  timeout          = 600

  values = [yamlencode({
    dex            = { enabled = false }
    notifications  = { enabled = false }
    applicationSet = { replicas = 0 }
    configs        = { params = { "server.insecure" = true } }
    server         = { resources = { requests = { cpu = "50m", memory = "96Mi" } } }
    repoServer     = { resources = { requests = { cpu = "50m", memory = "96Mi" } } }
    controller     = { resources = { requests = { cpu = "100m", memory = "192Mi" } } }
  })]
}
