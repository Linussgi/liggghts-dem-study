import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    new_df = df["time"]
    
    # Select columns that contain "lacey" in their name
    lacey_columns = [col for col in df.columns[2:] if "lacey" in col]
    new_df = pd.concat([new_df, df[lacey_columns]], axis=1)
    
    new_df.dropna(inplace=True)
    
    # Fitting starts at t = 2
    new_df = new_df[new_df["time"] >= 2] 
    
    return new_df


def model(t: np.ndarray, k: float, A: float) -> np.ndarray:
    return A * (1 - np.exp(-k * t))


def calculate_fit_quality(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    correlation_matrix = np.corrcoef(y_true, y_pred)
    r_squared = correlation_matrix[0, 1] ** 2
    
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    return r_squared, rmse


def fit_lacey_data(lacey_data: np.ndarray, time: np.ndarray) -> tuple[float, float, float]:
    A = np.max(lacey_data)

    def fitting_function(t, k):
        return model(t, k, A)

    popt, _ = curve_fit(fitting_function, time, lacey_data, p0=[0.1])
    k = popt[0]
    
    y_pred = fitting_function(time, k)
    r_squared, rmse = calculate_fit_quality(lacey_data, y_pred)
    
    return k, r_squared, rmse


def build_k_df(filtered_df: pd.DataFrame) -> pd.DataFrame:
    new_data = []

    # Get a list of lacey columns in the filtered DataFrame
    lacey_columns = [col for col in filtered_df.columns[1:] if "lacey" in col]

    # Iterate through the columns in blocks of 4 (x, y, z, r for each study)
    for i in range(0, len(lacey_columns), 4):
        row = []
        
        study_name = lacey_columns[i][:-7]
        row.append(study_name)
        
        # For each study data (x, y, z, r), fit the data
        k_values = []
        r_squared_values = []
        rmse_values = []
        
        for j in range(4):
            variable_column = lacey_columns[i + j]
            lacey_data = filtered_df[variable_column].values
            time = filtered_df.iloc[:, 0].values
            
            k_value, r_squared, rmse = fit_lacey_data(lacey_data, time)
            k_values.append(k_value)
            r_squared_values.append(r_squared)
            rmse_values.append(rmse)

        # Create new row for DataFrame
        row.extend(k_values)
        row.extend(r_squared_values)
        row.extend(rmse_values)
        new_data.append(row)

    dimensions = ["x", "y", "z", "r"]

    # Create column names for the new DataFrame
    columns = ["study name"]
    columns.extend([f"{dim} lacey k" for dim in dimensions])
    columns.extend([f"k{dim} Rsquared" for dim in dimensions])
    columns.extend([f"k{dim} RMSE" for dim in dimensions])
    
    new_df = pd.DataFrame(new_data, columns=columns)
    
    return new_df


lacey_results_path = "../lacey-files/lacye_results.csv"

df = pd.read_csv(lacey_results_path)
filtered_df = filter_df(df)
new_df = build_k_df(filtered_df)
print(f"Fitted k-values DataFrame created with shape {new_df.shape}")

new_df.to_csv("fitted_k_values.csv", index=False)
print("Fitted k-values saved to 'fitted_k_values.csv'")
