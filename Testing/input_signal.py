import matplotlib.pyplot as plt
import numpy as np

# Load the voltage data from the file
# Assuming the file contains one voltage value per line
file_path = './Testing/Test_Signal.txt'
voltage = np.loadtxt(file_path)

# Signal parameters provided
sampling_rate = 14000  # 14 kHz
num_samples = len(voltage)

# Create the time axis
# Time = Index / Sampling Rate
time = np.arange(num_samples) / sampling_rate

# Plotting
plt.figure(figsize=(12, 6))
plt.plot(time, voltage, label='Voltage Signal', color='b', linewidth=1)

# Formatting the plot
plt.title('Voltage vs. Time (Sampling Rate: 14 kHz)')
plt.xlabel('Time (seconds)')
plt.ylabel('Voltage (V)')
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

# Display the plot
plt.tight_layout()
plt.show()