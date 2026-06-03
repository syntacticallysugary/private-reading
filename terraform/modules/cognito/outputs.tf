output "client_id" {
  value       = aws_cognito_user_pool_client.private_reading.id
  description = "Cognito app client ID for Private Reading. Configure in the SPA and API Gateway."
}

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

output "hosted_ui_domain" {
  value       = "https://${aws_cognito_user_pool_domain.private_reading.domain}.auth.${var.aws_region}.amazoncognito.com"
  description = "Cognito Hosted UI base URL. Use as COGNITO_DOMAIN in the SPA config."
}
