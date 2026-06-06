# ── OCI identity ──────────────────────────────────────────────────────────────

variable "oci_tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}

variable "oci_user_ocid" {
  type        = string
  description = "OCI user OCID used for API calls."
}

variable "oci_fingerprint" {
  type        = string
  description = "Fingerprint of the OCI API signing key."
}

variable "oci_private_key" {
  type        = string
  sensitive   = true
  description = "PEM content of the OCI API private key (not a file path)."
}

variable "oci_region" {
  type        = string
  description = "OCI region identifier, e.g. us-ashburn-1."
}

variable "oci_compartment_ocid" {
  type        = string
  description = "OCI compartment OCID where all resources are created."
}

# ── AWS identity ──────────────────────────────────────────────────────────────

variable "aws_region" {
  type        = string
  description = "AWS region where the shared Cognito User Pool lives, e.g. us-east-1."
}

# ── Cognito (shared User Pool, managed by Know-It-All CloudFormation stack) ──

variable "cognito_user_pool_id" {
  type        = string
  description = "ID of the existing Cognito User Pool. Read-only — managed by Know-It-All CloudFormation."
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Globally unique domain prefix for the Cognito Hosted UI (e.g. private-reading-prod)."
  default     = "private-reading-prod"
}

# ── Application ───────────────────────────────────────────────────────────────

variable "app_name" {
  type        = string
  default     = "private-reading"
  description = "Short name used as a prefix for all resource display names and bucket names."
}

variable "environment" {
  type        = string
  default     = "prod"
  description = "Deployment environment label (prod | staging). Appended to resource names."

  validation {
    condition     = contains(["prod", "staging"], var.environment)
    error_message = "environment must be prod or staging."
  }
}

# ── Job Store ─────────────────────────────────────────────────────────────────

variable "job_store_url" {
  type        = string
  description = "Base URL of the SQLite job store service on the ARM VM, e.g. http://10.0.0.248:8000."
}

variable "job_store_api_key" {
  type        = string
  sensitive   = true
  description = "Shared secret for X-Job-Store-Token header sent by OCI Functions to the job store."
}

# ── Functions ─────────────────────────────────────────────────────────────────

variable "function_image" {
  type        = string
  description = "Fully qualified OCIR image URI for the API function, e.g. {region}.ocir.io/{namespace}/{repo}:{tag}."
  default     = ""
}

variable "function_memory_mb" {
  type        = number
  default     = 512
  description = "Memory allocated to the OCI Function in megabytes."
}

variable "function_timeout_s" {
  type        = number
  default     = 300
  description = "OCI Function execution timeout in seconds."
}

variable "worker_api_key" {
  type        = string
  sensitive   = true
  description = "Shared secret for authenticating worker poll requests against /worker/* routes."
}

variable "worker_webhook_url" {
  type        = string
  default     = ""
  description = "URL of the worker webhook receiver, e.g. http://192.168.1.105:8765/notify. Leave empty to disable push notifications (worker falls back to polling)."
}

variable "worker_webhook_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Shared secret sent in X-Webhook-Secret header to authenticate push notifications to the worker."
}

# ── Kubernetes (k3s cluster) ──────────────────────────────────────────────────

variable "k8s_host" {
  type        = string
  description = "k3s API server URL, e.g. https://192.168.1.x:6443."
  default     = ""
}

variable "k8s_cluster_ca_certificate" {
  type        = string
  sensitive   = true
  description = "Base64-encoded k3s cluster CA certificate."
  default     = ""
}

variable "k8s_client_certificate" {
  type        = string
  sensitive   = true
  description = "Base64-encoded client certificate for k3s authentication."
  default     = ""
}

variable "k8s_client_key" {
  type        = string
  sensitive   = true
  description = "Base64-encoded client key for k3s authentication."
  default     = ""
}
