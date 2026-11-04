import math

def advise(pod_count, cpu_used_m, cpu_request_m, peak_used_m):
    utilization = cpu_used_m / cpu_request_m * 100
    advice = []

    if utilization < 5:
        new_request = max(10, math.ceil(peak_used_m * 3))
        advice.append(f"Over-provisioned: lower CPU request from {cpu_request_m}m to {new_request}m.")
        if pod_count > 1:
            advice.append("Consider reducing replicas to 1 if high availability is not needed.")
    elif utilization < 20:
        new_request = max(10, math.ceil(peak_used_m * 3))
        advice.append(f"Somewhat over-provisioned: lower CPU request to about {new_request}m.")
    elif utilization <= 70:
        advice.append("Healthy: no change needed.")
    else:
        advice.append("Under pressure: raise the CPU limit or add replicas.")

    return utilization, advice

if __name__ == "__main__":
    # Real numbers from your Prometheus graph
    util, tips = advise(pod_count=2, cpu_used_m=0.25, cpu_request_m=100, peak_used_m=2)
    print(f"Utilization: {util:.2f}%")
    for tip in tips:
        print("-", tip)