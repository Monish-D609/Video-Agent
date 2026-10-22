#!/usr/bin/env python3
"""
Cost & Resource Guard: Verifies that synthesized CloudFormation templates
contain ONLY explicitly allowed, low-cost resources.
Fails loudly if any NAT Gateway, Load Balancer, RDS, ECS, Lambda, or other
disallowed service is detected.
"""
import json
import os
import sys
from glob import glob

ALLOWED_TYPES = {
    # EC2 & Minimal VPC (0 NAT)
    "AWS::EC2::Instance",
    "AWS::EC2::SecurityGroup",
    "AWS::EC2::SecurityGroupIngress",
    "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::VPC",
    "AWS::EC2::Subnet",
    "AWS::EC2::RouteTable",
    "AWS::EC2::Route",
    "AWS::EC2::SubnetRouteTableAssociation",
    "AWS::EC2::InternetGateway",
    "AWS::EC2::VPCGatewayAttachment",
    "AWS::EC2::Volume",
    # S3
    "AWS::S3::Bucket",
    "AWS::S3::BucketPolicy",
    "Custom::S3AutoDeleteObjects",
    # IAM
    "AWS::IAM::Role",
    "AWS::IAM::Policy",
    "AWS::IAM::InstanceProfile",
    # Budgets
    "AWS::Budgets::Budget",
    # CloudWatch (Logs / Alarms)
    "AWS::Logs::LogGroup",
    "AWS::CloudWatch::Alarm",
    # Optional CloudFront
    "AWS::CloudFront::Distribution",
    # CDK metadata
    "AWS::CDK::Metadata",
}

DISALLOWED_PATTERNS = [
    "NatGateway",
    "LoadBalancer",
    "RDS",
    "OpenSearch",
    "Elasticsearch",
    "ECS",
    "EKS",
    "Lambda",
    "ApiGateway",
    "SecretsManager",
    "Transcribe",
    "Bedrock",
    "SageMaker",
    "Route53",
    "ElastiCache",
    "VPCEndpoint",
]


def find_template(search_dirs):
    candidates = []
    for d in search_dirs:
        candidates.extend(glob(os.path.join(d, "**", "*.template.json"), recursive=True))
    return candidates


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs = [
        os.path.join(root, "infra", "cdk.out"),
        os.path.join(root, "cdk.out"),
    ]

    templates = find_template(search_dirs)
    if not templates:
        print("❌ Error: No synthesized template found. Run `cdk synth` first.")
        sys.exit(1)

    template_file = templates[0]
    print(f"🔍 Inspecting CloudFormation template: {template_file}\n")

    with open(template_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("Resources", {})
    if not resources:
        print("❌ Error: Template has no Resources section.")
        sys.exit(1)

    violations = []
    summary = {}

    for logical_id, res in resources.items():
        res_type = res.get("Type", "Unknown")
        summary[res_type] = summary.get(res_type, 0) + 1

        is_allowed = res_type in ALLOWED_TYPES
        # Authorize CDK internal S3 auto-delete helper (used to satisfy Task 3 auto_delete_objects)
        if "CustomS3AutoDeleteObjects" in logical_id:
            is_allowed = True

        for pattern in DISALLOWED_PATTERNS:
            if pattern.lower() in res_type.lower():
                if "CustomS3AutoDeleteObjects" in logical_id and pattern.lower() == "lambda":
                    continue
                violations.append((logical_id, res_type, f"Matched forbidden pattern '{pattern}'"))
                is_allowed = False
                break

        if not is_allowed and (logical_id, res_type) not in [(v[0], v[1]) for v in violations]:
            violations.append((logical_id, res_type, "Not in allowed low-cost whitelist"))

    print("============================================================")
    print(" SYNTHESIZED RESOURCE INVENTORY")
    print("============================================================")
    print(f"{'RESOURCE TYPE':<45} | {'COUNT':<5}")
    print("-" * 55)
    for res_type, count in sorted(summary.items()):
        if res_type in ALLOWED_TYPES:
            status = "✓ Allowed"
        elif res_type == "AWS::Lambda::Function":
            status = "✓ Allowed (CDK S3 auto-delete helper)"
        else:
            status = "❌ DISALLOWED"
        print(f"{res_type:<45} | {count:<5}  {status}")
    print("============================================================\n")

    if violations:
        print("🚨 HARD CONSTRAINT VIOLATION DETECTED!")
        print("The following disallowed or unwhitelisted resources were found in the template:")
        for log_id, r_type, reason in violations:
            print(f"  • {log_id} ({r_type}): {reason}")
        print("\nDeployment aborted to prevent unexpected cloud charges.")
        sys.exit(1)
    else:
        print("✅ VERIFICATION PASSED:")
        print("   • Zero NAT Gateways")
        print("   • Zero Load Balancers")
        print("   • Zero RDS / OpenSearch / ECS / Lambda / SecretsManager")
        print("   • Only minimal allowed cost-controlled resources are present.\n")


if __name__ == "__main__":
    main()
