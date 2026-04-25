from typing import TypedDict, Optional, Any

class PipelineState(TypedDict):
    audit_id: str
    file_path: str
    dataset_name: str
    total_rows: Optional[int]
    total_columns: Optional[int]
    protected_attributes: Optional[list[str]]
    features: Optional[list[str]]
    target: Optional[str]
    excluded: Optional[list[str]]
    null_summary: Optional[dict[str, float]]
    proxy_warnings: Optional[list[str]]
    column_details: Optional[list[dict]]
    schema_json: Optional[dict]
    bias_metrics: Optional[list[dict]]
    overall_risk: Optional[str]
    report_markdown: Optional[str]
    remediation_results: Optional[dict]
    status: Optional[str]
    error: Optional[str]
