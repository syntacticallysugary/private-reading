# ── Primary outputs — needed to configure the SPA and worker ──────────────────

output "api_base_url" {
  value       = module.api.api_base_url
  description = "API Gateway base URL. Set as API_BASE_URL in the SPA and worker ConfigMap."
}

output "web_bucket_url" {
  value       = module.storage.web_bucket_url
  description = "URL where the static SPA is served. Configure as the allowed origin in CORS."
}

output "cognito_client_id" {
  value       = module.cognito.client_id
  description = "Cognito app client ID. Set as COGNITO_CLIENT_ID in the SPA."
}

output "cognito_issuer" {
  value       = module.cognito.issuer
  description = "Cognito JWT issuer URL. Set as COGNITO_ISSUER in the SPA."
}

output "cognito_hosted_ui_domain" {
  value       = module.cognito.hosted_ui_domain
  description = "Cognito Hosted UI domain prefix. Full login URL: https://{domain}.auth.{region}.amazoncognito.com/login"
}

output "audiobooks_bucket_name" {
  value       = module.storage.audiobooks_bucket_name
  description = "Name of the OCI Object Storage bucket where Opus files are stored."
}

output "oci_namespace" {
  value       = data.oci_objectstorage_namespace.this.namespace
  description = "OCI Object Storage namespace. Needed for pre-signed URL construction."
}

# ── Secondary outputs — useful for debugging and CI/CD ───────────────────────

output "functions_application_id" {
  value       = module.functions.application_id
  description = "OCI Functions application OCID. Used by CI/CD fn deploy command."
}

output "db_id" {
  value       = module.database.db_id
  description = "Autonomous JSON Database OCID."
}
