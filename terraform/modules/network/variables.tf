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

variable "vcn_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the VCN."
}

variable "private_subnet_cidr" {
  type        = string
  default     = "10.0.1.0/24"
  description = "CIDR block for the private subnet used by OCI Functions."
}
