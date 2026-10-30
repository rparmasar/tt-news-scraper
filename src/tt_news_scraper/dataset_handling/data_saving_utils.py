"""Dataset export and saving utilities."""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def save_dataset(df: pd.DataFrame, output_path: str) -> None:
    """Export DataFrame to CSV with unified schema.

    Args:
        df: The DataFrame containing news articles
        output_path: Path to the output CSV file
    """
    df.to_csv(output_path, index=False)
    logger.info(f"Dataset saved to {output_path}")


def save_dataset_with_metadata(
    df: pd.DataFrame,
    output_path: str,
    metadata: Optional[dict] = None,
) -> None:
    """Export DataFrame to CSV with embedded metadata.

    Args:
        df: The DataFrame containing news articles
        output_path: Path to the output CSV file
        metadata: Optional dictionary of metadata (source, count, date_range, etc.)
    """
    if metadata is not None and len(metadata) > 0:
        meta_df = pd.DataFrame([metadata])
        df_with_meta = pd.concat(
            [meta_df.rename(columns={c: f"_meta_{c}" for c in metadata}), df],
            axis=1,
        )
    else:
        df_with_meta = df

    df_with_meta.to_csv(output_path, index=False)
    logger.info(f"Dataset with metadata saved to {output_path}")


def validate_dataframe_schema(df: pd.DataFrame, expected_columns: list[str]) -> bool:
    """Validate that DataFrame has the expected canonical columns.

    Args:
        df: The DataFrame to validate
        expected_columns: List of expected column names in order

    Returns:
        True if schema matches, False otherwise
    """
    actual_columns = list(df.columns)
    return actual_columns == expected_columns


def get_dataframe_summary(df: pd.DataFrame) -> dict:
    """Get a summary statistics dictionary for the DataFrame.

    Args:
        df: The DataFrame to summarize

    Returns:
        Dictionary with row count, column names, and basic stats per column
    """
    return {
        "row_count": len(df),
        "column_names": list(df.columns),
        "column_types": {col: str(type(df[col].iloc[0])) for col in df.columns},
        "non_null_counts": {col: df[col].notna().sum() for col in df.columns},
    }
