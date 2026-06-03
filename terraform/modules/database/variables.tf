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
