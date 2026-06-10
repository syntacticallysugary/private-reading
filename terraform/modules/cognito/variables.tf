variable "user_pool_id" {
  type        = string
  description = "ID of the existing Cognito User Pool (managed by Know-It-All CloudFormation — read-only)."
}

variable "aws_region" {
  type        = string
  description = "AWS region where the User Pool lives (e.g. us-east-1). Used to construct issuer and JWKS URLs."
}
