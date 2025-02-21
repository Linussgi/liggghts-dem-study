import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


def exponential_model(t: np.ndarray, k: float, A: float) -> np.ndarray:
    return A * (1 - np.exp(-k * t))


def fit_exponential(x_data: np.ndarray, y_data: np.ndarray) -> tuple[float, np.ndarray]:
    A = max(y_data)  

    # Perform curve fitting with k as parameter
    popt, _ = curve_fit(lambda t, k: exponential_model(t, k, A), x_data, y_data, p0=[0.1])
    k_fitted = popt[0]
    y_fitted = exponential_model(x_data, k_fitted, A)
    return k_fitted, y_fitted


def filter_df(df: pd.DataFrame, header_string: str) -> pd.DataFrame:
    # Get all column names that contain the specified header string
    filtered_columns = [col for col in df.columns if header_string in col]
    
    filtered_columns.append("time")

    df_new = df[filtered_columns].dropna()
    df_new = df_new[df_new["time"] > 1.9]

    return df_new


df = pd.read_csv("../lacey-files/lacey_results.csv")

header_string = "fric_2.000_cor_0.240" 
filtered_df = filter_df(df, header_string)

fig, ax = plt.subplots(2, 1, figsize=[12, 12]) 

x_data = filtered_df["time"]

# Simulation data ---------------------------------------------------------------------------
y1_data = filtered_df[header_string + " x lacey"]
y2_data = filtered_df[header_string + " y lacey"]
y3_data = filtered_df[header_string + " z lacey"]
y4_data = filtered_df[header_string + " r lacey"]

ax[0].errorbar(x_data, y1_data, yerr=None, fmt="-r", label="x mixing", linewidth=2, capsize=2)
ax[0].errorbar(x_data, y2_data, yerr=None, fmt="-b", label="y mixing", linewidth=2, capsize=2)
ax[0].errorbar(x_data, y3_data, yerr=None, fmt="-g", label="z mixing", linewidth=2, capsize=2)
ax[0].errorbar(x_data, y4_data, yerr=None, fmt="-k", label="r mixing", linewidth=2, capsize=2)

ax[0].set_xlabel("Time (s)", fontsize=10)
ax[0].set_ylabel("Mixing Index", fontsize=10)
ax[0].set_title(header_string, fontsize=12)
ax[0].legend()
ax[0].grid()

# Fitted model data --------------------------------------------------------------------------

# Perform fitting
k1, y1_fit = fit_exponential(x_data, y1_data)
k2, y2_fit = fit_exponential(x_data, y2_data)
k3, y3_fit = fit_exponential(x_data, y3_data)
k4, y4_fit = fit_exponential(x_data, y4_data)

ax[1].plot(x_data, y1_fit, "-r", label=f"Fitted x (k={k1:.4f})", linewidth=2)
ax[1].plot(x_data, y2_fit, "-b", label=f"Fitted y (k={k2:.4f})", linewidth=2)
ax[1].plot(x_data, y3_fit, "-g", label=f"Fitted z (k={k3:.4f})", linewidth=2)
ax[1].plot(x_data, y4_fit, "-k", label=f"Fitted r (k={k4:.4f})", linewidth=2)

ax[1].set_xlabel("Time", fontsize=10)
ax[1].set_ylabel("Mixing Index (Fitted)", fontsize=10)
ax[1].set_title("Fitted Exponential Models", fontsize=12)
ax[1].legend()
ax[1].grid()

plt.tight_layout()
plt.show()