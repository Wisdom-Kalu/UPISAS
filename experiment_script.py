import requests
import time
import csv
from datetime import datetime

# Define the URL endpoint
MONITOR_ENDPOINT = "http://127.0.0.1:50000/monitor"

# Define the function to process QoS metrics
def getQoSMetrics(oldSnapshots, newSnapshots):
    """
    Process the QoS metrics data.
    This function returns the average response time and availability for the snapshots.
    """
    averageResponseTime = 0
    averageAvailability = 0

    for snapshot in newSnapshots:
        instance_id = snapshot.get("instanceId", None)
        if not instance_id:
            print(f"Skipping snapshot: Missing instanceId.")
            continue

        oldest_snapshot = next((s for s in oldSnapshots if s.get("instanceId") == instance_id), None)

        if not oldest_snapshot:
            print(f"Skipping snapshot for instance {instance_id}: No matching snapshot in oldData.")
            continue

        # print({'OLD': oldest_snapshot})
        # print({'NEW': snapshot})
        avg_response_time, availability = compute_metrics_window(snapshot, oldest_snapshot)
        print(avg_response_time, availability)
        averageResponseTime += avg_response_time
        if availability is not None:
            averageAvailability += availability

    # Average metrics for all snapshots
    averageResponseTime = averageResponseTime / len(newSnapshots) if newSnapshots else 0
    averageAvailability = averageAvailability / len(newSnapshots) if newSnapshots else 0

    return averageAvailability, averageResponseTime

def savePerformanceMetrics(oldData, newData):
    """
    Save the performance metrics to a CSV file along with the timestamp.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for service_id, service_data in newData.items():
        snapshots = service_data.get("snapshot", [])
        if not snapshots:
            print(f"Skipping service {service_id}: No snapshots available.")
            continue

        old_snapshots = oldData.get(service_id, {}).get("snapshot", [])
        averageAvailability, averageResponseTime = getQoSMetrics(old_snapshots, snapshots)
        
        # Save the metrics to CSV
        save_metrics_to_csv(service_id, averageAvailability, averageResponseTime, timestamp)

def save_metrics_to_csv(service_id, avg_availability, avg_response_time, timestamp):
    """
    Append the performance metrics to a CSV file.
    """
    file_name = "NimNawWis.csv"
    # Check if the CSV file exists and write headers if not
    file_exists = False
    try:
        with open(file_name, mode='r'):
            file_exists = True
    except FileNotFoundError:
        pass
    
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            # Write headers if the file is new
            writer.writerow(["Timestamp", "Service ID", "Average Availability (%)", "Average Response Time (ms)"])

        # Write the performance data for the service
        writer.writerow([timestamp, service_id, avg_availability, avg_response_time])

def compute_metrics_window(latest_snapshot, oldest_snapshot):
        """
        Computes the average response time and availability within a time window
        by comparing the latest snapshot and the oldest snapshot using httpMetrics only.
        """
        successful_requests_duration = 0
        successful_requests_count = 0
        total_requests_count = 0

        # Compare httpMetrics between latest and oldest snapshots
        latest_http_metrics = latest_snapshot.get("httpMetrics", {})
        oldest_http_metrics = oldest_snapshot.get("httpMetrics", {})

        # print(f"DEBUG: Latest snapshot httpMetrics: {latest_http_metrics}")
        # print(f"DEBUG: Oldest snapshot httpMetrics: {oldest_http_metrics}")

        for endpoint, metrics in latest_http_metrics.items():
            # Extract metrics for SUCCESS outcome
            latest_success = metrics.get("outcomeMetrics", {}).get("SUCCESS", {})
            oldest_success = oldest_http_metrics.get(endpoint, {}).get("outcomeMetrics", {}).get("SUCCESS", {})

            # Increment successful duration and count
            duration_diff = latest_success.get("totalDuration", 0) - oldest_success.get("totalDuration", 0)
            count_diff = latest_success.get("count", 0) - oldest_success.get("count", 0)

            if duration_diff < 0 or count_diff < 0:
                print(f"WARNING: Negative difference detected for endpoint {endpoint}. Skipping this endpoint.")
                continue

            successful_requests_duration += duration_diff
            successful_requests_count += count_diff

            # Calculate total requests by summing all outcomes
            for outcome, outcome_metrics in metrics.get("outcomeMetrics", {}).items():
                latest_total = outcome_metrics.get("count", 0)
                oldest_total = oldest_http_metrics.get(endpoint, {}).get("outcomeMetrics", {}).get(outcome, {}).get("count", 0)
                total_requests_count += latest_total - oldest_total

        # Calculate average response time
        avg_response_time = successful_requests_duration / successful_requests_count if successful_requests_count > 0 else 0
        print(f"Average Response Time: {avg_response_time}")

        # Calculate availability
        availability = (successful_requests_count / total_requests_count) * 100 if total_requests_count > 0 else 0
        print(f"Availability: {availability}")

        return avg_response_time, availability



# Function to fetch data from the monitor endpoint
def fetchData():
    try:
        response = requests.get(MONITOR_ENDPOINT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except ValueError:
        print("Error parsing JSON response.")

# Main script to fetch data every 20 seconds
if __name__ == "__main__":
    print("Starting data monitoring...")
    oldData = {}
    i=1
    while True:
        newData = fetchData()
        savePerformanceMetrics(oldData, newData)
        print(f'Saved Metric Record ${i}')
        oldData = newData
        i = i+1
        time.sleep(20)  # Wait for 20 seconds before the next fetch
