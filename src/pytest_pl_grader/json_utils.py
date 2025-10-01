import json
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd


def to_json(v: Any) -> Any:
    if isinstance(v, np.number):
        return {
            "_type": "np_scalar",
            "_concrete_type": type(v).__name__,
            "_value": str(v),
        }
    elif isinstance(v, np.bool_):
        return {
            "_type": "np_bool",
            "_value": str(v),
        }
    elif isinstance(v, np.ndarray):
        if np.isrealobj(v):
            return {"_type": "ndarray", "_value": v.tolist(), "_dtype": str(v.dtype)}
        elif np.iscomplexobj(v):
            return {
                "_type": "complex_ndarray",
                "_value": {"real": v.real.tolist(), "imag": v.imag.tolist()},
                "_dtype": str(v.dtype),
            }
    elif isinstance(v, pd.DataFrame):
        # The next lines of code are required to address the JSON table-orient
        # generating numeric keys instead of strings for an index sequence with
        # only numeric values (c.f. pandas-dev/pandas#46392)
        df_modified_names = v.copy()

        if df_modified_names.columns.dtype in (np.float64, np.int64):  # type: ignore
            df_modified_names.columns = df_modified_names.columns.astype("string")

        # For version 2 storing a data frame, we use the table orientation alongside of
        # enforcing a date format to allow for passing datetime and missing (`pd.NA`/`np.nan`) values
        # Details: https://pandas.pydata.org/docs/reference/api/pandas.read_json.html
        # Convert to JSON string with escape characters
        encoded_json_str_df = df_modified_names.to_json(orient="table", date_format="iso")
        # Export to native JSON structure
        pure_json_df = json.loads(encoded_json_str_df)

        return {"_type": "dataframe_v2", "_value": pure_json_df}
    else:
        return v


def _has_value_fields(v, fields: list[str]) -> bool:
    """Return True if all fields in the '_value' dictionary are present."""
    return "_value" in v and isinstance(v["_value"], dict) and all(field in v["_value"] for field in fields)


def from_json(v_json) -> Any:
    if isinstance(v_json, dict) and "_type" in v_json:
        if v_json["_type"] == "complex":
            if _has_value_fields(v_json, ["real", "imag"]):
                return complex(v_json["_value"]["real"], v_json["_value"]["imag"])
            else:
                raise ValueError("variable of type complex should have value with real and imaginary pair")
        elif v_json["_type"] == "np_bool":
            if "_value" in v_json:
                return np.bool_(v_json["_value"] == "True")
            else:
                raise ValueError("variable of type np_bool should have value")
        elif v_json["_type"] == "np_scalar":
            if "_concrete_type" in v_json and "_value" in v_json:
                return getattr(np, v_json["_concrete_type"])(v_json["_value"])
            else:
                raise ValueError(f"variable of type {v_json['_type']} needs both concrete type and value information")
        elif v_json["_type"] == "ndarray":
            if "_value" in v_json:
                if "_dtype" in v_json:
                    return np.array(v_json["_value"]).astype(v_json["_dtype"])
                else:
                    return np.array(v_json["_value"])
            else:
                raise ValueError("variable of type ndarray should have value")
        elif v_json["_type"] == "complex_ndarray":
            if _has_value_fields(v_json, ["real", "imag"]):
                if "_dtype" in v_json:
                    return (np.array(v_json["_value"]["real"]) + np.array(v_json["_value"]["imag"]) * 1j).astype(v_json["_dtype"])
                else:
                    return np.array(v_json["_value"]["real"]) + np.array(v_json["_value"]["imag"]) * 1j
            else:
                raise ValueError("variable of type complex_ndarray should have value with real and imaginary pair")
        elif v_json["_type"] == "dataframe_v2":
            # Convert native JSON back to a string representation so that
            # pandas read_json() can process it.
            value_str = StringIO(json.dumps(v_json["_value"]))
            return pd.read_json(value_str, orient="table")
        else:
            raise ValueError("variable has unknown type {}".format(v_json["_type"]))
    return v_json
