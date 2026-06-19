# BlockSupply — AWS Pricing Analysis

## Summary

For a class project / demo workload (low traffic, single instance, no
Multi-AZ), this architecture is **fully covered by the AWS Free Tier** for
the first 12 months on a new AWS account. The table below shows both the
free-tier cost (what you'll actually pay) and the standard on-demand cost
(what it would cost after the free tier expires, or on an account that has
already used it), so the tradeoffs are visible either way.

Prices are approximate (region: **ap-south-1, Mumbai**) — AWS pricing
changes periodically, so for an exact quote use the
[AWS Pricing Calculator](https://calculator.aws/).

## Cost Breakdown

| Component | Spec used | Free Tier (first 12 months) | Standard On-Demand (after Free Tier) |
|---|---|---|---|
| **EC2** | t2.micro, 1 instance, 24/7 | $0.00 — 750 hrs/month included | ≈ $9–10 / month |
| **EBS (EC2 storage)** | 20 GB gp2 | $0.00 — 30 GB included | ≈ $2 / month |
| **RDS (MariaDB)** | db.t3.micro, Single-AZ, 20 GB | $0.00 — 750 hrs/month + 20 GB storage included | ≈ $22–24 / month (instance) + ≈ $2 / month (storage) |
| **S3** | < 1 GB reports/documents, low request volume | $0.00 — 5 GB + 20,000 GET / 2,000 PUT included | ≈ $0.03 / GB-month + request costs (negligible at this scale) |
| **CloudWatch** | Default EC2/RDS metrics + a few custom metrics | $0.00 — basic monitoring is free | Custom metrics ≈ $0.30/metric/month beyond free allotment (10 metrics free) |
| **Data Transfer Out** | Demo-level traffic | $0.00 — 100 GB/month free (account-wide) | $0.09/GB beyond 100 GB |
| **IAM** | Roles, no extra resources | $0.00 (always free) | $0.00 (always free) |
| **VPC** | No NAT Gateway used | $0.00 | N/A (NAT Gateway, if added later, is ≈ $0.045/hr + data — avoided in this design) |

### Estimated Monthly Total

- **On Free Tier (new account, first 12 months): ~$0/month**
- **After Free Tier expires: ~$33–36/month**, dominated by the RDS instance hours (the single most expensive line item in this architecture)

## Cost Optimization Notes

1. **No NAT Gateway** — the private subnet has no outbound internet route, which avoids the ~$32+/month NAT Gateway cost (a common surprise in student AWS bills). RDS doesn't need outbound internet for this app.
2. **Single-AZ RDS** — Multi-AZ would roughly double the RDS cost; not justified for a demo workload.
3. **t2.micro / db.t3.micro** — both are the smallest burstable instance classes, sufficient for low-traffic dashboard usage.
4. **S3 lifecycle rule (optional)** — for a production version, an S3 lifecycle policy moving reports older than 90 days to S3 Glacier would reduce storage costs further; not necessary at this scale.
5. **Stop instances when not in use** — since EC2/RDS are billed hourly, stopping both outside of demo/grading windows avoids any free-tier overage if hours run close to the 750/month cap (unlikely for a single instance, but relevant if multiple students/instances share an account).

## Reference

- AWS Free Tier overview: https://aws.amazon.com/free/
- AWS Pricing Calculator: https://calculator.aws/
- RDS Pricing: https://aws.amazon.com/rds/pricing/
- EC2 Pricing: https://aws.amazon.com/ec2/pricing/on-demand/
