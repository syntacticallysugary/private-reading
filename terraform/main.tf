# ── Providers ─────────────────────────────────────────────────────────────────

provider "oci" {
  tenancy_ocid = var.oci_tenancy_ocid
  user_ocid    = var.oci_user_ocid
  fingerprint  = var.oci_fingerprint
  private_key  = var.oci_private_key
  region       = var.oci_region
}

provider "aws" {
  region = var.aws_region
}

# Kubernetes provider is configured but only used when k8s variables are set.
# It is left unconfigured (empty) until the k3s cluster is bootstrapped.
provider "kubernetes" {
  host                   = var.k8s_host
  cluster_ca_certificate = var.k8s_host != "" ? base64decode(var.k8s_cluster_ca_certificate) : null
  client_certificate     = var.k8s_host != "" ? base64decode(var.k8s_client_certificate) : null
  client_key             = var.k8s_host != "" ? base64decode(var.k8s_client_key) : null
}

# ── OCI namespace (tenancy-scoped, needed for Object Storage) ─────────────────

data "oci_objectstorage_namespace" "this" {
  compartment_id = var.oci_compartment_ocid
}

# ── Cognito app client ────────────────────────────────────────────────────────
# Runs first — its outputs (issuer, jwks_uri, client_id) flow into api and functions.

module "cognito" {
  source = "./modules/cognito"

  user_pool_id  = var.cognito_user_pool_id
  app_name      = var.app_name
  spa_origin    = module.storage.web_bucket_url
  aws_region    = var.aws_region
  domain_prefix = var.cognito_domain_prefix
}

# ── Network (VCN + private subnet + service gateway) ─────────────────────────

module "network" {
  source = "./modules/network"

  compartment_ocid = var.oci_compartment_ocid
  app_name         = var.app_name
  environment      = var.environment
}

# ── Storage (web bucket + audiobooks bucket + lifecycle policy) ───────────────

module "storage" {
  source = "./modules/storage"

  compartment_ocid = var.oci_compartment_ocid
  app_name         = var.app_name
  environment      = var.environment
  namespace        = data.oci_objectstorage_namespace.this.namespace
  oci_region       = var.oci_region
}

# ── Database (OCI NoSQL, Always Free) ────────────────────────────────────────

module "database" {
  source = "./modules/database"

  compartment_ocid = var.oci_compartment_ocid
  app_name         = var.app_name
  environment      = var.environment
}

# ── Functions (OCI Functions app + API function + IAM) ───────────────────────

module "functions" {
  source = "./modules/functions"

  compartment_ocid       = var.oci_compartment_ocid
  app_name               = var.app_name
  environment            = var.environment
  subnet_id              = module.network.private_subnet_id
  image                  = var.function_image
  memory_mb              = var.function_memory_mb
  timeout_s              = var.function_timeout_s
  nosql_table_name       = module.database.table_name
  worker_api_key         = var.worker_api_key
  worker_webhook_url     = var.worker_webhook_url
  worker_webhook_secret  = var.worker_webhook_secret
  oci_region             = var.oci_region
  namespace              = data.oci_objectstorage_namespace.this.namespace
  audiobooks_bucket_name = module.storage.audiobooks_bucket_name
  cognito_issuer         = module.cognito.issuer
  cognito_client_id      = module.cognito.client_id
}

# ── API Gateway ───────────────────────────────────────────────────────────────
# Needs a public subnet — reuse network module's private subnet is insufficient.
# The API Gateway requires a public subnet to receive inbound internet traffic.
# A minimal public subnet is created inline here to keep the network module
# focused on the Functions private subnet.

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = module.network.vcn_id
  display_name   = "${var.app_name}-${var.environment}-igw"
  enabled        = true
}

resource "oci_core_route_table" "public" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = module.network.vcn_id
  display_name   = "${var.app_name}-${var.environment}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.oci_compartment_ocid
  vcn_id         = module.network.vcn_id
  display_name   = "${var.app_name}-${var.environment}-public-sl"

  ingress_security_rules {
    description = "Allow inbound HTTPS from internet"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    protocol    = "6"
    stateless   = false
    tcp_options {
      min = 443
      max = 443
    }
  }

  egress_security_rules {
    description      = "Allow all outbound traffic"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    protocol         = "all"
    stateless        = false
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.oci_compartment_ocid
  vcn_id            = module.network.vcn_id
  display_name      = "${var.app_name}-${var.environment}-public-subnet"
  cidr_block        = "10.0.0.0/24"
  dns_label         = "public"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.public.id]
}

module "api" {
  source = "./modules/api"

  compartment_ocid  = var.oci_compartment_ocid
  app_name          = var.app_name
  environment       = var.environment
  subnet_id         = oci_core_subnet.public.id
  function_id       = module.functions.function_id
  spa_origin        = module.storage.web_bucket_url
  cognito_issuer    = module.cognito.issuer
  cognito_jwks_uri  = module.cognito.jwks_uri
  cognito_client_id = module.cognito.client_id
}
