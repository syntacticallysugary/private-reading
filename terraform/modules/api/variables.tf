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
  description = "OCID of the subnet for the API Gateway. Must be a public subnet."
}

variable "function_id" {
  type        = string
  description = "OCID of the OCI Function that handles all API routes."
}

variable "spa_origin" {
  type        = string
  description = "Origin of the static web app (Object Storage bucket URL). Used in CORS policy."
}

variable "cognito_issuer" {
  type        = string
  description = "Cognito JWT issuer URL — https://cognito-idp.{region}.amazonaws.com/{pool_id}."
}

variable "cognito_jwks_uri" {
  type        = string
  description = "Cognito JWKS endpoint URL for JWT validation."
}

variable "cognito_client_id" {
  type        = string
  description = "Cognito app client ID. Used as the expected JWT audience."
}
