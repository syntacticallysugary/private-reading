locals {
  prefix = "${var.app_name}-${var.environment}"
}

# ── Dynamic group — identifies the Function as a resource principal ───────────
# Allows the Function to authenticate to OCI services (Object Storage, ADB)
# using its own identity, without storing credentials in function config.

resource "oci_identity_dynamic_group" "functions" {
  compartment_id = var.compartment_ocid
  name           = "${local.prefix}-functions-dg"
  description    = "Dynamic group for ${local.prefix} OCI Functions resource principal auth."

  # Matches all functions in this compartment
  matching_rule = "ALL {resource.type = 'fnfunc', resource.compartment.id = '${var.compartment_ocid}'}"
}

# ── IAM policies ──────────────────────────────────────────────────────────────

resource "oci_identity_policy" "functions" {
  compartment_id = var.compartment_ocid
  name           = "${local.prefix}-functions-policy"
  description    = "Allows ${local.prefix} Functions to access Object Storage and Autonomous DB."

  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.functions.name} to manage object-family in tenancy",
    "Allow dynamic-group ${oci_identity_dynamic_group.functions.name} to manage nosql-family in tenancy",
  ]
}

resource "oci_identity_policy" "apigateway_invoke" {
  compartment_id = var.compartment_ocid
  name           = "${local.prefix}-apigateway-invoke-policy"
  description    = "Allows API Gateway to invoke ${local.prefix} Functions."

  statements = [
    "Allow any-user to use functions-family in compartment id ${var.compartment_ocid} where ALL {request.principal.type = 'ApiGateway', request.resource.compartment.id = '${var.compartment_ocid}'}",
  ]
}

# ── Functions application ─────────────────────────────────────────────────────

resource "oci_functions_application" "this" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.prefix}-app"
  subnet_ids     = [var.subnet_id]

  # Shared config injected into all functions in this application
  config = {
    OCI_REGION             = var.oci_region
    OCI_NAMESPACE          = var.namespace
    AUDIOBOOKS_BUCKET      = var.audiobooks_bucket_name
    COGNITO_ISSUER         = var.cognito_issuer
    COGNITO_CLIENT_ID      = var.cognito_client_id
    NOSQL_TABLE_NAME       = var.nosql_table_name
    NOSQL_COMPARTMENT_ID   = var.compartment_ocid
    WORKER_API_KEY         = var.worker_api_key
    WORKER_WEBHOOK_URL     = var.worker_webhook_url
    WORKER_WEBHOOK_SECRET  = var.worker_webhook_secret
  }
}

# ── API function ──────────────────────────────────────────────────────────────
# Single function handles all routes. Internal routing is done in Python.
# The function image is built and pushed by the CI/CD pipeline; the image URI
# is passed in via var.image. During initial terraform apply the placeholder
# image is used — replace it on first deploy.

resource "oci_functions_function" "api" {
  # Skipped until a real OCIR image is built and pushed in Step 2.
  count = var.image != "" ? 1 : 0

  application_id     = oci_functions_application.this.id
  display_name       = "${local.prefix}-api"
  image              = var.image
  memory_in_mbs      = var.memory_mb
  timeout_in_seconds = var.timeout_s

}
