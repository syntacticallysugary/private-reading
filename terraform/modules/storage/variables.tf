variable "compartment_ocid" {
  type        = string
  description = "OCI compartment OCID."
}

variable "app_name" {
  type        = string
  description = "Application name prefix for resource display names."
}

variable "environment" {
  type        = string
  description = "Deployment environment label."
}

variable "namespace" {
  type        = string
  description = "OCI Object Storage namespace (tenancy namespace)."
}

variable "api_gateway_origin" {
  type        = string
  description = "API Gateway base URL, used in the audiobooks bucket CORS policy."
  default     = ""
}

variable "oci_region" {
  type        = string
  description = "OCI region (e.g. us-chicago-1). Used to name the Object Storage service principal in lifecycle IAM policy."
}

variable "audiobook_retention_days" {
  type        = number
  default     = 2
  description = "Days after which completed audiobook files are automatically deleted."
}
