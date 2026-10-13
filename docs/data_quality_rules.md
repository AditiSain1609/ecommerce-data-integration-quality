# Data quality rules

| Dimension | Rule | Failure handling |
|---|---|---|
| Completeness | Required entity columns are non-null | Row rejected where implemented |
| Validity | Emails match a basic address shape; prices/amounts nonnegative; quantities positive; known order statuses; parseable dates | Row rejected and issue retained |
| Uniqueness | Duplicate entity identifiers after first occurrence | Later row quarantined |
| Referential integrity | Orders reference customers; items reference orders/products; payments reference orders | Child row quarantined and issue recorded |
| Consistency | Order item line amount is quantity × unit price | Derived during transform; header comparison is not currently a rejection rule |
| Timeliness | Source date parseability is checked | No lateness threshold is configured |
| Schema | Required fields must exist | File extraction fails before loading |

Completeness = present required cells / all required cells. Validity = accepted rows / checked rows. Uniqueness = distinct business-key rows / checked rows. Empty denominators produce 100%. Accuracy is omitted because no trusted ground truth exists. Referential integrity currently has issue counts but no score column in the summary.
