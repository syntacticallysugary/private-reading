variable "user_pool_id" {
  type        = string
  description = "ID of the existing Cognito User Pool (managed by Know-It-All CloudFormation — read-only)."
}

variable "app_name" {
  type        = string
  description = "Application name, used as the Cognito app client display name."
}

variable "spa_origin" {
  type        = string
  description = "SPA base URL (Object Storage bucket URL). Used for Cognito callback and logout URLs."
}

variable "aws_region" {
  type        = string
  description = "AWS region where the User Pool lives (e.g. us-east-1). Used to construct issuer and JWKS URLs."
}

variable "domain_prefix" {
  type        = string
  description = "Globally unique prefix for the Cognito Hosted UI domain. Full URL: https://{prefix}.auth.{region}.amazoncognito.com."
}
