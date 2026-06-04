variable "compartment_ocid" {
  type        = string
  description = "OCI compartment OCID."
}

variable "app_name" {
  type        = string
  description = "Application name prefix."
}

variable "environment" {
  type        = string
  description = "Deployment environment label."
}

variable "subnet_id" {
  type        = string
  description = "OCID of the private subnet for the Functions application."
}

variable "image" {
  type        = string
  description = "Fully qualified OCIR image URI for the function."
}

variable "memory_mb" {
  type        = number
  default     = 512
  description = "Memory allocated to the function in MB."
}

variable "timeout_s" {
  type        = number
  default     = 300
  description = "Function execution timeout in seconds."
}

variable "nosql_table_name" {
  type        = string
  description = "Name of the OCI NoSQL jobs table."
}

variable "worker_api_key" {
  type        = string
  sensitive   = true
  description = "Shared secret for authenticating worker poll requests."
}

variable "worker_webhook_url" {
  type        = string
  default     = ""
  description = "Worker webhook receiver URL. Empty disables push notifications."
}

variable "worker_webhook_secret" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Shared secret for X-Webhook-Secret header on push notifications."
}

variable "oci_region" {
  type        = string
  description = "OCI region, passed through to the function config."
}

variable "namespace" {
  type        = string
  description = "OCI Object Storage namespace."
}

variable "audiobooks_bucket_name" {
  type        = string
  description = "Name of the private audiobooks Object Storage bucket."
}

variable "cognito_issuer" {
  type        = string
  description = "Cognito JWT issuer URL, e.g. https://cognito-idp.{region}.amazonaws.com/{pool_id}."
}

variable "cognito_client_id" {
  type        = string
  description = "Cognito app client ID for this application."
}
