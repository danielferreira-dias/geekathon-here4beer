import io
from typing import Optional

import pandas as pd
from fastapi import UploadFile, HTTPException


def _read_file_to_dataframe(upload: UploadFile) -> pd.DataFrame:
    filename = upload.filename or "uploaded"
    suffix = (filename.split(".")[-1] or "").lower()
    try:
        content = upload.file.read()
    finally:
        upload.file.seek(0)
    if not content:
        raise HTTPException(status_code=400, detail=f"File {filename} is empty")

    buffer = io.BytesIO(content)
    try:
        if suffix in {"csv"}:
            df = pd.read_csv(buffer)
        elif suffix in {"xls", "xlsx"}:
            df = pd.read_excel(buffer)
        else:
            # Try CSV first, then Excel as fallback
            try:
                buffer.seek(0)
                df = pd.read_csv(buffer)
            except Exception:
                buffer.seek(0)
                df = pd.read_excel(buffer)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse {filename}: {e}")

    if df.empty:
        raise HTTPException(status_code=400, detail=f"File {filename} contained no rows")
    return df


def upload_to_csv_text(upload: UploadFile) -> str:
    """
    Reads an uploaded CSV/XLSX file into a pandas DataFrame and returns canonical CSV text.
    Ensures index is not included and headers are present.
    """
    df = _read_file_to_dataframe(upload)
    # Normalize column names to simple strings
    df.columns = [str(c) for c in df.columns]
    csv_text = df.to_csv(index=False)
    return csv_text
