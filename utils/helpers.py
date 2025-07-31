from typing import Dict, Any

def calculate_apr(funding_rate: float, payout_frequency_hours: int) -> float:
    """
    Calculates an estimated aggregated Annual Percentage Rate (APR) from a funding rate.
    
    Args:
        funding_rate (float): The funding rate for a single period (e.g., 0.0001).
        payout_frequency_hours (int): The number of hours in the funding period (e.g., 8, 4, or 1).
        
    Returns:
        The estimated APR as a percentage (e.g., 10.95 for a 0.01% rate every 8 hours).
    """
    if payout_frequency_hours <= 0:
        raise ValueError("Payout frequency must be positive.")
        
    periods_per_day = 24 / payout_frequency_hours
    daily_rate = funding_rate * periods_per_day
    annual_rate = daily_rate * 365
    
    return annual_rate * 100

# Example Usage
if __name__ == '__main__':
    # Example: A 0.01% funding rate paid every 8 hours
    rate = 0.0001
    frequency = 8
    apr = calculate_apr(rate, frequency)
    print(f"A funding rate of {rate*100:.4f}% every {frequency} hours is approximately {apr:.2f}% APR.")

    # Example: A 0.005% funding rate paid every 4 hours
    rate = 0.00005
    frequency = 4
    apr = calculate_apr(rate, frequency)
    print(f"A funding rate of {rate*100:.4f}% every {frequency} hours is approximately {apr:.2f}% APR.")
