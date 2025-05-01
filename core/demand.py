"""
Demand generation functions for inventory simulations.
"""
import numpy as np
import math
from typing import Optional, Union, List, Dict, Any

def parse_seasonal_pattern(
    seasonal_pattern: str,
    num_periods: int
) -> List[float]:
    """
    Parse a comma-separated string of seasonal factors and normalize it to the required number of periods.
    Each value in the pattern represents a segment of the total period.
    
    Args:
        seasonal_pattern: Comma-separated string of seasonal factors or 'flat'
        num_periods: Number of periods to generate
        
    Returns:
        List of seasonal factors for each period
    """
    # Handle special case for 'flat' pattern
    if seasonal_pattern == 'flat':
        return [1.0] * num_periods
    
    # Parse the comma-separated values
    values = [float(x.strip()) for x in seasonal_pattern.split(',') if x.strip()]
    
    if not values:
        raise ValueError("seasonal_pattern must contain at least one value")
    
    # Normalize the values to ensure they average to 1.0
    avg = sum(values) / len(values)
    normalized_values = [v / avg for v in values]
    
    # Calculate how many periods each value should cover
    pattern_length = len(normalized_values)
    periods_per_segment = num_periods / pattern_length
    
    # Create the expanded pattern
    expanded_pattern = []
    
    for i in range(num_periods):
        # Determine which segment this period belongs to
        segment_index = int(i / periods_per_segment)
        # Handle edge case for the last period
        if segment_index >= pattern_length:
            segment_index = pattern_length - 1
        
        expanded_pattern.append(normalized_values[segment_index])
    
    return expanded_pattern

def calculate_seasonality_factor(
    day: int,
    weight: float = 1.0,
    seasonal_pattern: Optional[List[float]] = None
) -> float:
    """
    Calculate seasonality factor based on day of year or custom pattern.
    
    Args:
        day: Day number (1-based)
        weight: Weight of seasonality effect (0.0 = no effect, higher = stronger effect)
        seasonal_pattern: Custom seasonal pattern (list of factors)
        
    Returns:
        Seasonality factor (multiplier for demand)
    """
    if seasonal_pattern is not None:
        # Use custom seasonal pattern
        index = (day - 1) % len(seasonal_pattern)
        base_seasonality = seasonal_pattern[index]
        
        # Apply weight (additive approach to prevent zero demand)
        # When weight=0, seasonality=1.0 (no effect)
        # When weight=1, seasonality=base_seasonality
        weighted_seasonality = 1.0 + (base_seasonality - 1.0) * weight
        
        return weighted_seasonality
    else:
        # Use default flat pattern (no seasonality)
        return 1.0

def calculate_trend_factor(
    day: int,
    weight: float = 1.0,
    monthly_rate: float = 0.01
) -> float:
    """
    Calculate trend factor based on day.
    
    Args:
        day: Day number
        weight: Weight of trend effect (0.0 = no effect, higher = stronger effect)
        monthly_rate: Monthly growth rate (e.g., 0.01 = 1% growth per month)
        
    Returns:
        Trend factor (multiplier for demand)
    """
    if weight == 0.0:
        return 1.0
    
    # Calculate months since start
    months = day / 30.0
    
    # Calculate compound growth
    trend = (1.0 + monthly_rate) ** months
    
    # Apply weight (additive approach)
    weighted_trend = 1.0 + ((trend - 1.0) * weight)
    
    return weighted_trend

def generate_demand(
    demand_mean: float,
    demand_distribution: str,
    demand_dispersion_parameter: Optional[float],
    day: int,
    seasonality_weight: float = 1.0,
    trend_weight: float = 0.0,
    noise_weight: float = 1.0,
    trend_monthly_rate: float = 0.01,
    seasonal_pattern: Optional[Union[str, List[float]]] = None,
    num_periods: Optional[int] = None,
    round_to_int: bool = True
) -> Union[int, float]:
    """
    Generate demand based on parameters.
    
    Args:
        demand_mean: Mean demand
        demand_distribution: Distribution type ('normal', 'poisson', 'gamma', 'lognormal')
        demand_dispersion_parameter: Dispersion parameter (std dev for normal, shape for gamma, etc.)
        day: Day number
        seasonality_weight: Weight of seasonality effect
        trend_weight: Weight of trend effect
        noise_weight: Weight of random noise
        trend_monthly_rate: Monthly growth rate for trend
        seasonal_pattern: Custom seasonal pattern (comma-separated string or list of factors)
        num_periods: Number of periods (required if seasonal_pattern is a string)
        round_to_int: Whether to round demand to integer
        
    Returns:
        Generated demand
    """
    # Validate inputs
    if demand_mean < 0:
        raise ValueError("demand_mean must be non-negative")
    
    if demand_distribution not in ['normal', 'poisson', 'gamma', 'lognormal']:
        raise ValueError(f"Invalid demand_distribution: {demand_distribution}")
    
    # Parse seasonal pattern if provided as string
    parsed_seasonal_pattern = None
    if seasonal_pattern is not None:
        if isinstance(seasonal_pattern, str):
            if num_periods is None:
                raise ValueError("num_periods is required when seasonal_pattern is a string")
            parsed_seasonal_pattern = parse_seasonal_pattern(seasonal_pattern, num_periods)
        elif isinstance(seasonal_pattern, list):
            parsed_seasonal_pattern = seasonal_pattern
    
    # Start with base demand
    adjusted_mean = demand_mean
    
    # Apply seasonality if pattern is provided
    if parsed_seasonal_pattern is not None:
        seasonality_factor = calculate_seasonality_factor(day, seasonality_weight, parsed_seasonal_pattern)
        adjusted_mean = demand_mean * seasonality_factor
    
    # Apply trend if trend_weight > 0
    if trend_weight > 0:
        trend_factor = calculate_trend_factor(day, trend_weight, trend_monthly_rate)
        adjusted_mean = adjusted_mean * trend_factor
    
    # If noise_weight is 0, return deterministic demand
    if noise_weight == 0:
        demand = adjusted_mean
    else:
        # Generate demand based on distribution
        if demand_distribution == 'normal':
            if demand_dispersion_parameter is None:
                raise ValueError("demand_dispersion_parameter is required for normal distribution")
            
            # Use absolute noise (not relative to mean)
            noise = demand_dispersion_parameter * noise_weight
            
            # Generate demand from normal distribution
            demand = np.random.normal(adjusted_mean, noise)
            
            # Ensure non-negative demand
            demand = max(0, demand)
        
        elif demand_distribution == 'poisson':
            # For Poisson, we can't directly control variance (variance = mean)
            # But we can simulate higher variance by using a negative binomial distribution
            # or by scaling the mean and then scaling the result
            if noise_weight == 1.0:
                # Standard Poisson (variance = mean)
                demand = np.random.poisson(adjusted_mean)
            else:
                # Use negative binomial to simulate over-dispersed Poisson
                # In negative binomial, variance = mean + mean²/r where r is the dispersion parameter
                # Lower r = higher variance
                r = 1.0 / max(0.01, noise_weight - 1.0)  # Ensure r is positive
                p = r / (r + adjusted_mean)
                demand = np.random.negative_binomial(r, p)
        
        elif demand_distribution == 'gamma':
            if demand_dispersion_parameter is None:
                raise ValueError("demand_dispersion_parameter is required for gamma distribution")
            
            # For gamma, we use dispersion_parameter as the shape parameter
            # and calculate scale to maintain the desired mean
            # Apply noise_weight to control variability
            shape = demand_dispersion_parameter / noise_weight  # Lower shape = higher variance
            scale = adjusted_mean / shape
            
            # Generate demand from gamma distribution
            demand = np.random.gamma(shape, scale)
        
        elif demand_distribution == 'lognormal':
            if demand_dispersion_parameter is None:
                raise ValueError("demand_dispersion_parameter is required for lognormal distribution")
            
            # For lognormal, we need to convert mean and std to mu and sigma
            # If X is lognormal, then log(X) is normal with parameters mu and sigma
            # E[X] = exp(mu + sigma^2/2)
            # Var[X] = (exp(sigma^2) - 1) * exp(2*mu + sigma^2)
            
            # We use dispersion_parameter as the coefficient of variation (CV = std/mean)
            # Apply noise_weight to control variability
            cv = demand_dispersion_parameter * noise_weight
            
            # Calculate sigma from CV
            sigma = np.sqrt(np.log(1 + cv**2))
            
            # Calculate mu from mean and sigma
            mu = np.log(adjusted_mean) - (sigma**2) / 2
            
            # Generate demand from lognormal distribution
            demand = np.random.lognormal(mu, sigma)
    
    # Round to integer if requested
    if round_to_int:
        demand = round(demand)
    
    return demand

def generate_seasonal_demand(
    day: int,
    demand_mean: float,
    demand_distribution: str = 'normal',
    demand_dispersion_parameter: Optional[float] = 2.0,
    seasonality_weight: float = 1.0,
    trend_weight: float = 0.0,
    noise_weight: float = 1.0,
    trend_monthly_rate: float = 0.01,
    seasonal_pattern: Optional[Union[str, List[float]]] = None,
    num_periods: Optional[int] = None,
    round_to_int: bool = True
) -> Union[int, float]:
    """
    Generate seasonal demand based on parameters.
    
    Args:
        day: Day number
        demand_mean: Mean demand
        demand_distribution: Distribution type ('normal', 'poisson', 'gamma', 'lognormal')
        demand_dispersion_parameter: Dispersion parameter (std dev for normal, shape for gamma, etc.)
        seasonality_weight: Weight of seasonality effect
        trend_weight: Weight of trend effect
        noise_weight: Weight of random noise
        trend_monthly_rate: Monthly growth rate for trend
        seasonal_pattern: Custom seasonal pattern (comma-separated string or list of factors)
        num_periods: Number of periods (required if seasonal_pattern is a string)
        round_to_int: Whether to round demand to integer
        
    Returns:
        Generated seasonal demand
    """
    return generate_demand(
        demand_mean=demand_mean,
        demand_distribution=demand_distribution,
        demand_dispersion_parameter=demand_dispersion_parameter,
        day=day,
        seasonality_weight=seasonality_weight,
        trend_weight=trend_weight,
        noise_weight=noise_weight,
        trend_monthly_rate=trend_monthly_rate,
        seasonal_pattern=seasonal_pattern,
        num_periods=num_periods,
        round_to_int=round_to_int
    )

def generate_demand_series(
    demand_mean: float,
    demand_distribution: str,
    demand_dispersion_parameter: Optional[float],
    start_day: int,
    num_days: int,
    seasonality_weight: float = 1.0,
    trend_weight: float = 0.0,
    noise_weight: float = 1.0,
    trend_monthly_rate: float = 0.01,
    seasonal_pattern: Optional[Union[str, List[float]]] = None,
    round_to_int: bool = True
) -> List[Union[int, float]]:
    """
    Generate a series of demand values.
    
    Args:
        demand_mean: Mean demand
        demand_distribution: Distribution type ('normal', 'poisson', 'gamma', 'lognormal')
        demand_dispersion_parameter: Dispersion parameter (std dev for normal, shape for gamma, etc.)
        start_day: Starting day number
        num_days: Number of days to generate
        seasonality_weight: Weight of seasonality effect
        trend_weight: Weight of trend effect
        noise_weight: Weight of random noise
        trend_monthly_rate: Monthly growth rate for trend
        seasonal_pattern: Custom seasonal pattern (comma-separated string or list of factors)
        round_to_int: Whether to round demand to integer
        
    Returns:
        List of generated demand values
    """
    demand_series = []
    
    # Parse seasonal pattern if provided as string
    parsed_seasonal_pattern = None
    if seasonal_pattern is not None:
        if isinstance(seasonal_pattern, str):
            parsed_seasonal_pattern = parse_seasonal_pattern(seasonal_pattern, num_days)
        elif isinstance(seasonal_pattern, list):
            parsed_seasonal_pattern = seasonal_pattern
    
    for day_offset in range(num_days):
        day = start_day + day_offset
        
        demand = generate_demand(
            demand_mean=demand_mean,
            demand_distribution=demand_distribution,
            demand_dispersion_parameter=demand_dispersion_parameter,
            day=day,
            seasonality_weight=seasonality_weight,
            trend_weight=trend_weight,
            noise_weight=noise_weight,
            trend_monthly_rate=trend_monthly_rate,
            seasonal_pattern=parsed_seasonal_pattern,
            num_periods=num_days,
            round_to_int=round_to_int
        )
        
        demand_series.append(demand)
    
    return demand_series
