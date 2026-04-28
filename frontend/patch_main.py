import re

with open("/home/shrey/Fairlens/ML/files/main.py", "r") as f:
    content = f.read()

# Replace the GET /remediate route to POST
# Find @app.get("/remediate/{audit_id}") to the end of the file.

match = re.search(r'@app\.get\("/remediate/\{audit_id\}"\).*?def remediate_dataset.*?raise HTTPException\(status_code=500, detail=str\(e\)\)', content, re.DOTALL)
if match:
    old_func = match.group(0)
    
    new_func = """@app.post("/remediate/{audit_id}")
async def remediate(
    audit_id: str,
    file: UploadFile = File(...),
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    \"\"\"
    Generate debiased dataset. Accepts the original CSV again because
    raw data is never persisted in memory across server restarts.
    Models are loaded from DB if not already in memory.
    \"\"\"
    user_id = _user_id_from_headers(authorization, x_user_id)

    # If this audit's models aren't in memory, load them from DB
    if _state.get("audit_id") != audit_id or not _state.get("trained"):
        try:
            load_models_into_state(audit_id)
        except DatabaseOperationError as e:
            raise _db_http_error(e)

    # Verify ownership
    _load_owned_audit(audit_id, user_id)

    # Parse uploaded CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(400, detail=f"Could not parse CSV: {e}")

    # Store raw_df in state so get_debiased_predictions() works
    _state["raw_df"] = df.copy()

    # Run debiased predictions
    try:
        export_df = get_debiased_predictions()
    except Exception as e:
        raise HTTPException(400, detail=str(e))

    # Add sensitive col back
    sensitive_col = _state["sensitive_col"]
    target_col    = _state["target_col"]
    aligned_df    = df.iloc[:len(export_df)]
    export_df[sensitive_col] = aligned_df[sensitive_col].values

    # Rename debiased_decision → target_col so it re-uploads cleanly
    original_decisions = export_df["baseline_decision"].values
    debiased_decisions = export_df["debiased_decision"].values
    export_df[target_col] = debiased_decisions

    # Compute summary stats
    rows_changed   = int((original_decisions != debiased_decisions).sum())
    pct_changed    = round(rows_changed / len(export_df) * 100, 1)

    from fairlearn.metrics import demographic_parity_ratio
    from pipeline import encode_sensitive
    A, _, _, _ = encode_sensitive(export_df[sensitive_col])
    original_di = float(demographic_parity_ratio(
        export_df[target_col].values, original_decisions, sensitive_features=A
    ))
    debiased_di = float(demographic_parity_ratio(
        export_df[target_col].values, debiased_decisions, sensitive_features=A
    ))

    # Drop helper columns
    export_df.drop(
        columns=["baseline_decision", "debiased_decision", "bias_detected"],
        errors="ignore", inplace=True
    )

    summary = {
        "rows_changed":       rows_changed,
        "pct_changed":        pct_changed,
        "original_di_ratio":  round(original_di, 3),
        "debiased_di_ratio":  round(debiased_di, 3),
    }

    dataset_name = _state.get("dataset_name") or "dataset.csv"
    out_filename = f"debiased_{dataset_name}"

    return Response(
        content=export_df.to_csv(index=False),
        media_type="text/csv",
        headers={
            "Content-Disposition":    f'attachment; filename="{out_filename}"',
            "X-Remediation-Summary":  json.dumps(summary),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Remediation-Summary",
        },
    )"""

    content = content.replace(old_func, new_func)
    with open("/home/shrey/Fairlens/ML/files/main.py", "w") as f:
        f.write(content)
    print("Patched main.py")
else:
    print("Could not find match")
