The evolution from the AWS Certified Solutions Architect – Professional SAP‑C01 exam to the SAP‑C02 exam reflects one of the most significant shifts in AWS architectural expectations in the last decade. The new exam blueprint places far greater emphasis on modern cloud‑native architectures, distributed systems patterns, and operational excellence in environments that increasingly rely on automation, event‑driven design, and managed services. Many services that were peripheral, optional, or entirely absent in SAP‑C01 have now moved into the center of the SAP‑C02 competency model. This shift mirrors the real‑world movement of enterprise workloads toward serverless, containerized, and highly automated architectures.

One of the most prominent additions to SAP‑C02 is AWS CloudFormation Registry and Resource Types, which did not exist in the SAP‑C01 era. The exam now expects architects to understand how third‑party and custom resource types can be registered, versioned, and governed within CloudFormation. This reflects the industry trend toward infrastructure standardization and the need for organizations to treat infrastructure as a modular, governed product rather than a collection of templates. Architects must now understand how to extend CloudFormation with private resource types, enforce schema compliance, and integrate these resources with CI/CD pipelines. The SAP‑C02 exam assumes familiarity with drift detection, resource import, and the nuances of stack‑set governance across multi‑account environments.

Another major addition is AWS Cloud Control API (CCAPI). This service did not exist during SAP‑C01 and represents a new abstraction layer for provisioning AWS and third‑party resources using a consistent API. The SAP‑C02 exam expects candidates to understand how CCAPI enables consistent CRUD operations across resource providers, how it integrates with CloudFormation Registry, and how it supports multi‑cloud or hybrid provisioning tools. While CCAPI is not yet widely adopted in the field, AWS clearly sees it as a foundational capability for future infrastructure automation, and the exam reflects that direction.

The SAP‑C02 exam also introduces AWS Proton, a service that was not part of SAP‑C01 and is now considered a key tool for platform engineering teams. Proton provides a managed environment for deploying standardized microservice and serverless application templates. The exam expects architects to understand how Proton enables platform teams to define versioned templates, enforce compliance, and provide self‑service deployment capabilities to developers. This aligns with the broader industry movement toward internal developer platforms (IDPs) and the need for organizations to scale microservices without losing governance or consistency.

A significant shift in SAP‑C02 is the expanded coverage of AWS AppConfig, which was not emphasized in SAP‑C01. AppConfig is now treated as a first‑class service for configuration management, feature flagging, and safe deployment practices. The exam expects candidates to understand how AppConfig integrates with Lambda, ECS, EKS, and EC2, how it supports validators and deployment strategies, and how it enables controlled rollouts with automatic rollback. This reflects the modern architectural expectation that configuration should be decoupled from code and deployed with the same rigor as application artifacts.

Another major addition is Amazon EventBridge Pipes, a service that did not exist during SAP‑C01. Pipes provide a managed way to connect event sources to targets with filtering, enrichment, and transformation. The SAP‑C02 exam expects architects to understand how Pipes simplify event‑driven architectures by eliminating the need for custom polling, glue code, or Lambda fan‑out patterns. EventBridge Pipes represent AWS’s push toward more declarative event routing, and the exam reflects this by including scenarios where Pipes reduce operational overhead compared to traditional Lambda‑based integrations.

The SAP‑C02 exam also includes EventBridge Scheduler, another service absent from SAP‑C01. Scheduler provides a scalable, serverless cron‑like system for invoking targets across AWS. Unlike CloudWatch Events, Scheduler supports millions of schedules, flexible time windows, and high‑precision invocation. The exam expects candidates to understand when Scheduler is preferred over Step Functions, CloudWatch Events, or Lambda‑based scheduling mechanisms.

A major new area in SAP‑C02 is AWS Step Functions Distributed Map, which did not exist during SAP‑C01. Distributed Map enables massively parallel processing of large datasets, with each item processed as an independent workflow. The exam expects architects to understand how Distributed Map differs from standard Map states, how it integrates with S3, and how it enables large‑scale parallelism without custom orchestration. This reflects AWS’s push toward serverless data processing patterns that replace EMR or custom EC2‑based batch systems.

Another important addition is Amazon EKS Blueprints, which were not part of SAP‑C01. While EKS itself existed, the SAP‑C02 exam now expects familiarity with the ecosystem of tools that support enterprise‑grade Kubernetes deployments. This includes GitOps patterns, add‑on management, cluster lifecycle automation, and multi‑account governance. The exam reflects the reality that Kubernetes has become a mainstream enterprise platform, and architects must understand how to deploy and manage it at scale.

The SAP‑C02 exam also introduces Amazon EKS Anywhere and EKS on Outposts, neither of which were part of SAP‑C01. These services reflect AWS’s hybrid and edge strategy, and the exam expects candidates to understand how EKS can be deployed outside AWS while maintaining consistent tooling, governance, and operational models. This includes understanding the differences between EKS Anywhere, EKS on Outposts, and self‑managed Kubernetes clusters.

Another major addition is AWS Fault Injection Simulator (FIS). Chaos engineering was not part of SAP‑C01, but SAP‑C02 now expects architects to understand how to design resilient systems using controlled fault injection. This includes simulating network latency, API throttling, instance termination, and dependency failures. The exam reflects the industry shift toward proactive resilience testing rather than reactive troubleshooting.

The SAP‑C02 exam also expands coverage of AWS Backup, which was only lightly touched in SAP‑C01. The new exam expects candidates to understand cross‑account backup, backup vault locking, backup policies, and integration with services like EFS, DynamoDB, and Aurora. This reflects the increasing regulatory and compliance requirements around data protection.

Another new area is AWS Systems Manager Fleet Manager, which did not exist during SAP‑C01. Fleet Manager provides a unified interface for managing servers across AWS and on‑premises environments. The exam expects candidates to understand how Fleet Manager integrates with SSM, how it supports hybrid environments, and how it reduces the need for traditional management tools.

The SAP‑C02 exam also includes Amazon VPC Lattice, a major new service that was not part of SAP‑C01. Lattice provides application‑level connectivity across VPCs, accounts, and environments. The exam expects candidates to understand how Lattice simplifies service‑to‑service communication, replaces complex mesh architectures, and integrates with IAM for fine‑grained authorization. This is one of the most significant additions to the exam, reflecting AWS’s push toward simplifying multi‑VPC architectures.

Another major addition is AWS Verified Access, which did not exist during SAP‑C01. Verified Access provides secure, VPN‑less access to internal applications using Zero Trust principles. The exam expects candidates to understand how Verified Access integrates with identity providers, device posture checks, and application‑level policies. This reflects the industry shift toward Zero Trust architectures and away from traditional VPN‑based access models.

The SAP‑C02 exam also includes Amazon GuardDuty Malware Protection, GuardDuty EKS Runtime Monitoring, and GuardDuty Lambda Protection, none of which existed during SAP‑C01. The exam expects candidates to understand how GuardDuty now provides deep runtime visibility across containers, serverless workloads, and EC2 instances. This reflects AWS’s expansion of GuardDuty from a network‑focused service to a full‑stack threat detection platform.

Another major addition is AWS Security Hub Automated Response and Remediation, which was not part of SAP‑C01. The exam expects candidates to understand how Security Hub integrates with EventBridge, Lambda, and Step Functions to automatically remediate findings. This reflects the industry trend toward automated security operations and continuous compliance.

The SAP‑C02 exam also includes Amazon Detective for EKS, another service absent from SAP‑C01. Detective now supports container‑level forensic analysis, and the exam expects candidates to understand how it integrates with GuardDuty and EKS audit logs.

Another important addition is AWS Network Firewall, which was not emphasized in SAP‑C01. The SAP‑C02 exam expects candidates to understand how Network Firewall provides stateful inspection, intrusion prevention, and domain filtering across VPCs. This reflects the increasing complexity of multi‑VPC architectures and the need for centralized network security controls.

The SAP‑C02 exam also includes AWS WAF Bot Control, WAF Fraud Control, and WAF Account Takeover Prevention, none of which were part of SAP‑C01. These services reflect AWS’s expansion into application‑level threat mitigation, and the exam expects candidates to understand how these features integrate with CloudFront, ALB, and API Gateway.

Another major addition is Amazon OpenSearch Serverless, which did not exist during SAP‑C01. The exam expects candidates to understand how OpenSearch Serverless provides automatic scaling, encryption, and multi‑tenant isolation without cluster management. This reflects AWS’s push toward serverless analytics and search workloads.

The SAP‑C02 exam also includes Amazon Athena for Apache Spark, another new service. The exam expects candidates to understand how Athena Spark enables interactive data processing using Spark without managing clusters. This reflects AWS’s broader movement toward serverless data analytics.

Another important addition is AWS Glue Data Quality, which did not exist during SAP‑C01. The exam expects candidates to understand how Glue Data Quality provides rule‑based and ML‑based data quality checks across ETL pipelines. This reflects the increasing importance of data governance in enterprise architectures.

The SAP‑C02 exam also includes AWS Lake Formation Governed Tables, which were not part of SAP‑C01. Governed Tables provide ACID transactions, row‑level security, and fine‑grained access control for data lakes. The exam expects candidates to understand how Governed Tables integrate with Glue, Athena, and EMR.

Another major addition is Amazon S3 Express One Zone, a new storage class not present in SAP‑C01. The exam expects candidates to understand how Express One Zone provides extremely low latency and high throughput for high‑performance workloads. This reflects AWS’s push toward specialized storage tiers for analytics and machine learning.

The SAP‑C02 exam also includes S3 Multi‑Region Access Points, which did not exist during SAP‑C01. The exam expects candidates to understand how MRAPs provide global request routing, failover, and multi‑region replication. This reflects the increasing need for global architectures with low latency and high resilience.

Another important addition is Amazon FSx for OpenZFS, which was not part of SAP‑C01. The exam expects candidates to understand how FSx for OpenZFS provides high‑performance file storage with advanced snapshot and cloning capabilities.

The SAP‑C02 exam also includes Amazon FSx for NetApp ONTAP enhancements, including SnapMirror replication and multi‑AZ deployments. These features were not part of SAP‑C01 and reflect AWS’s deepening partnership with NetApp.

Another major addition is AWS Application Composer, a visual tool for designing serverless applications. The exam expects candidates to understand how Application Composer integrates with SAM, CloudFormation, and IaC workflows.

The SAP‑C02 exam also includes AWS SAM Accelerate, which did not exist during SAP‑C01. SAM Accelerate provides rapid feedback loops for serverless development, and the exam expects candidates to understand how it improves developer productivity.

Another important addition is Amazon CodeCatalyst, a new DevOps platform not present in SAP‑C01. The exam expects candidates to understand how CodeCatalyst provides CI/CD, issue tracking, and project orchestration in a unified environment.

The SAP‑C02 exam also includes AWS Resilience Hub, which did not exist during SAP‑C01. Resilience Hub provides automated resilience assessments, recommendations, and compliance checks. The exam expects candidates to understand how Resilience Hub integrates with FIS, CloudWatch, and architecture diagrams.

Another major addition is AWS Application Migration Service (MGN), which replaces CloudEndure and was not part of SAP‑C01. The exam expects candidates to understand how MGN provides automated lift‑and‑shift migrations with minimal downtime.

The SAP‑C02 exam also includes AWS Migration Hub Refactor Spaces, another service absent from SAP‑C01. Refactor Spaces provides a managed environment for incremental microservices migration using the strangler‑fig pattern.

Another important addition is AWS PrivateLink enhancements, including cross‑account and cross‑VPC service connectivity patterns that were not part of SAP‑C01.

The SAP‑C02 exam also includes Amazon Route 53 Application Recovery Controller (ARC), a major new service for multi‑region failover and readiness checks. The exam expects candidates to understand how ARC provides zonal and regional health checks, routing controls, and failover orchestration.

Another major addition is AWS Global Accelerator enhancements, including endpoint weighting, traffic dials, and multi‑region routing patterns that were not emphasized in SAP‑C01.

The SAP‑C02 exam also includes Amazon MQ for RabbitMQ, which did not exist during SAP‑C01. The exam expects candidates to understand how RabbitMQ differs from ActiveMQ and when each is appropriate.

Another important addition is Amazon SNS FIFO, which was not part of SAP‑C01. The exam expects candidates to understand how SNS FIFO provides ordered, exactly‑once message delivery.

The SAP‑C02 exam also includes Amazon SQS high‑throughput FIFO, another new feature. The exam expects candidates to understand how high‑throughput FIFO enables large‑scale ordered messaging.

Another major addition is Amazon API Gateway HTTP APIs, which were not part of SAP‑C01. The exam expects candidates to understand how HTTP APIs differ from REST APIs in cost, performance, and feature set.

The SAP‑C02 exam also includes Lambda SnapStart, a major new feature that dramatically reduces cold starts. The exam expects candidates to understand how SnapStart works, its limitations, and its impact on Java workloads.

Another important addition is Lambda Function URLs, which did not exist during SAP‑C01. The exam expects candidates to understand when Function URLs are preferred over API Gateway.

The SAP‑C02 exam also includes Lambda response streaming, another new feature. The exam expects candidates to understand how streaming responses reduce latency for large payloads.

Another major addition is Amazon DynamoDB import/export from S3, which was not part of SAP‑C01. The exam expects candidates to understand how this feature enables large‑scale data movement without consuming write capacity.

The SAP‑C02 exam also includes DynamoDB incremental backups, point‑in‑time recovery enhancements, and global table improvements, none of which were emphasized in SAP‑C01.

Another important addition is Amazon Aurora Serverless v2, which replaces v1 and was not part of SAP‑C01. The exam expects candidates to understand how v2 provides near‑instant scaling and predictable performance.

The SAP‑C02 exam also includes RDS Blue/Green Deployments, a major new feature. The exam expects candidates to understand how Blue/Green enables safe, low‑downtime upgrades.

Another major addition is Amazon Redshift Serverless, which did not exist during SAP‑C01. The exam expects candidates to understand how Redshift Serverless provides automatic scaling and cost‑efficient analytics.

The SAP‑C02 exam also includes Redshift Multi‑AZ, another new feature. The exam expects candidates to understand how Multi‑AZ improves resilience and availability.

Another important addition is Amazon EMR Serverless, which replaces EMR on EC2 for many workloads. The exam expects candidates to understand how EMR Serverless simplifies big data processing.

The SAP‑C02 exam also includes AWS Glue Streaming ETL, which was not part of SAP‑C01. The exam expects candidates to understand how Glue Streaming processes real‑time data with low latency.

Another major addition is Amazon Kinesis Data Streams On‑Demand, which did not exist during SAP‑C01. The exam expects candidates to understand how On‑Demand eliminates shard management.

The SAP‑C02 exam also includes Kinesis Video Streams WebRTC, another new feature. The exam expects candidates to understand how WebRTC enables low‑latency video streaming.

Another important addition is Amazon SageMaker Serverless Inference, which was not part of SAP‑C01. The exam expects candidates to understand how serverless inference reduces cost for intermittent ML workloads.

The SAP‑C02 exam also includes SageMaker Inference Recommender, another new feature. The exam expects candidates to understand how it automates instance selection for ML models.

Another major addition is AWS IoT TwinMaker, which did not exist during SAP‑C01. The exam expects candidates to understand how TwinMaker enables digital twins for industrial systems.

The SAP‑C02 exam also includes AWS IoT FleetWise, another new service. The exam expects candidates to understand how FleetWise collects and transforms vehicle telemetry.

Another important addition is AWS Clean Rooms, which did not exist during SAP‑C01. The exam expects candidates to understand how Clean Rooms enable secure data collaboration without sharing raw data.

The SAP‑C02 exam also includes AWS Supply Chain, another new service. The exam expects candidates to understand how Supply Chain provides visibility and analytics across supply networks.

Another major addition is Amazon Connect Contact Lens, which was not part of SAP‑C01. The exam expects candidates to understand how Contact Lens provides real‑time sentiment analysis and agent assistance.

The SAP‑C02 exam also includes Amazon Connect Wisdom, another new feature. The exam expects candidates to understand how Wisdom provides knowledge retrieval for contact center agents.

Another important addition is AWS Billing Conductor, which did not exist during SAP‑C01. The exam expects candidates to understand how Billing Conductor enables custom billing rates and cost allocation.

The SAP‑C02 exam also includes AWS Cost Anomaly Detection, another new feature. The exam expects candidates to understand how anomaly detection identifies unexpected cost spikes.

Another major addition is AWS Organizations Service Control Policy (SCP) enhancements, including delegated administrators and policy guardrails that were not part of SAP‑C01.

The SAP‑C02 exam also includes IAM Roles Anywhere, a major new capability. The exam expects candidates to understand how Roles Anywhere enables X.509‑based authentication for external workloads.

Another important addition is IAM Access Analyzer policy generation, which did not exist during SAP‑C01. The exam expects candidates to understand how Access Analyzer generates least‑privilege policies.

The SAP‑C02
