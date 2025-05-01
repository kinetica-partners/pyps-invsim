import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gamma

# Input variables from Excel file
start_inventory = xl("B20")
mean_demand = xl("B15")
std_demand = xl("B14")
reorder_point = xl("B21")
reorder_quantity = xl("B22")
lead_time_mean = xl("B30")
lead_time_shape = xl("B29")
num_periods = xl("B11")
num_scenarios = xl("B12")

# Function to simulate inventory levels (unchanged)
def simulate_inventory(start_inv, mean_demand, std_demand, reorder_point, reorder_qty, lead_time):
    inventory = [start_inv]
    pending_orders = []
    
    for day in range(1, num_periods):
        # Process pending orders
        for order in pending_orders:
            if order['arrival'] == day:
                inventory.append(inventory[-1] + order['quantity'])
                pending_orders.remove(order)
                break
        else:
            inventory.append(inventory[-1])
        
        # Generate daily demand
        demand = max(0, np.random.normal(mean_demand, std_demand))
        inventory[-1] = max(0, inventory[-1] - demand)
        
        # Check reorder point
        if inventory[-1] <= reorder_point and not pending_orders:
            lt = int(gamma.rvs(lead_time_shape, scale=lead_time_mean/lead_time_shape))
            pending_orders.append({'arrival': day + lt, 'quantity': reorder_qty})
    
    return inventory

# Run simulations
all_scenarios = [simulate_inventory(start_inventory, mean_demand, std_demand, 
                                    reorder_point, reorder_quantity, lead_time_mean) 
                 for _ in range(num_scenarios)]

# Calculate statistics
min_levels = [min(scenario) for scenario in all_scenarios]
avg_levels = [np.mean(scenario) for scenario in all_scenarios]

# Generate daily demands and lead times for histograms
daily_demands = [max(0, np.random.normal(mean_demand, std_demand)) for _ in range(10000)]
lead_times = [int(gamma.rvs(lead_time_shape, scale=lead_time_mean/lead_time_shape)) for _ in range(10000)]

# Plotting
plt.figure(figsize=(15, 12))

# Random walk plot
plt.subplot(2, 1, 1)
for scenario in all_scenarios[:100]:  # Plot first 100 scenarios for clarity
    plt.plot(scenario)
plt.title('Inventory Level Random Walk')
plt.xlabel('Period')
plt.ylabel('Inventory Level')

# Function to add percentile lines to histogram
def add_percentile_lines(ax, data):
    percentile_5 = np.percentile(data, 5)
    percentile_95 = np.percentile(data, 95)
    ax.axvline(percentile_5, color='red', linestyle=':', label='5th percentile')
    ax.axvline(percentile_95, color='red', linestyle=':', label='95th percentile')
    ax.legend()

# Histograms
plt.subplot(2, 4, 5)
plt.hist(min_levels, bins=30)
plt.title('Minimum Inventory Level')
add_percentile_lines(plt.gca(), min_levels)

plt.subplot(2, 4, 6)
plt.hist(avg_levels, bins=30)
plt.title('Average Inventory Level')
add_percentile_lines(plt.gca(), avg_levels)

plt.subplot(2, 4, 7)
plt.hist(daily_demands, bins=30)
plt.title('Daily Demand')
add_percentile_lines(plt.gca(), daily_demands)

plt.subplot(2, 4, 8)
plt.hist(lead_times, bins=range(min(lead_times), max(lead_times) + 2, 1))
plt.title('Lead Time Distribution')
add_percentile_lines(plt.gca(), lead_times)

plt.tight_layout()
plt.show()