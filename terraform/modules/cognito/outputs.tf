output "user_pool_id" {
  value       = data.aws_cognito_user_pool.shared.id
  description = "Cognito User Pool ID (pass-through from input variable)."
}

output "issuer" {
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${var.user_pool_id}"
  description = "Cognito JWT issuer URL. Configure in the API Gateway JWT authorizer."
}

output "jwks_uri" {
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${var.user_pool_id}/.well-known/jwks.json"
  description = "Cognito JWKS endpoint. Configure in the API Gateway JWT authorizer."
}
