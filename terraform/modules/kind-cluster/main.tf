# Local Kubernetes cluster using kind (Kubernetes-in-Docker).
# One control-plane node that also runs workloads: ~600-900 MB RAM.

resource "kind_cluster" "this" {
  name            = var.cluster_name
  node_image      = "kindest/node:${var.kubernetes_version}"
  wait_for_ready  = true
  kubeconfig_path = var.kubeconfig_path

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    networking {
      # kindnet (default CNI) enforces NetworkPolicy since kind v0.24
      api_server_address = "127.0.0.1"
    }

    node {
      role = "control-plane"

      # Label so the ingress controller can be pinned here
      kubeadm_config_patches = [
        <<-EOT
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
        EOT
      ]

      # Traefik NodePorts -> your laptop (http://devsecops360.localtest.me:8088)
      extra_port_mappings {
        container_port = 30080
        host_port      = var.http_host_port
        listen_address = "127.0.0.1"
        protocol       = "TCP"
      }
      extra_port_mappings {
        container_port = 30443
        host_port      = var.https_host_port
        listen_address = "127.0.0.1"
        protocol       = "TCP"
      }
    }

    dynamic "node" {
      for_each = range(var.worker_count)
      content {
        role = "worker"
      }
    }
  }
}
