"""
Forecasting functions for inventory simulations.
"""
import numpy as np
from typing import List, Optional, Union, Dict, Any

def calculate_moving_average(
    history: List[float],
    window: int
) -> float:
    """
    Calculate moving average of a time series.
    
    Args:
        history: Historical values
        window: Window size
        
    Returns:
        Moving average
    """
    if not history:
        return 0.0
    
    if len(history) < window:
        # If history is shorter than window, use all available data
        return sum(history) / len(history)
    
    # Calculate moving average using the last 'window' values
    return sum(history[-window:]) / window

def handle_early_period_forecasting(
    history: List[float],
    strategy: str = 'use_available',
    default_value: float = 0.0
) -> float:
    """
    Handle forecasting in early periods when history is limited.
    
    Args:
        history: Historical values
        strategy: Strategy for early period forecasting ('use_available', 'use_mean', 'use_default')
        default_value: Default value to use if strategy is 'use_default'
        
    Returns:
        Forecast value
    """
    if not history:
        return default_value
    
    if strategy == 'use_available':
        # Use average of available data
        return sum(history) / len(history)
    
    elif strategy == 'use_mean':
        # Use mean of available data
        return np.mean(history)
    
    elif strategy == 'use_default':
        # Use default value
        return default_value
    
    else:
        raise ValueError(f"Invalid early period strategy: {strategy}")

def generate_forecast(
    history: List[float],
    forecast_type: str,
    window: int = 30,
    horizon: int = 1,
    early_period_strategy: str = 'use_available',
    default_value: float = 0.0
) -> Union[float, List[float]]:
    """
    Generate forecast based on historical data.
    
    Args:
        history: Historical values
        forecast_type: Type of forecast ('naive', 'moving_average')
        window: Window size for moving average
        horizon: Forecast horizon
        early_period_strategy: Strategy for early period forecasting
        default_value: Default value to use if strategy is 'use_default'
        
    Returns:
        Forecast value or list of forecast values
    """
    if not history:
        if horizon == 1:
            return default_value
        else:
            return [default_value] * horizon
    
    if forecast_type == 'naive':
        # Naive forecast uses the last observed value
        forecast_value = history[-1]
    
    elif forecast_type == 'moving_average':
        # Moving average forecast
        forecast_value = calculate_moving_average(history, window)
    
    else:
        raise ValueError(f"Invalid forecast_type: {forecast_type}")
    
    # Return single value or list based on horizon
    if horizon == 1:
        return forecast_value
    else:
        return [forecast_value] * horizon

def calculate_rolling_forecast(
    history: List[float],
    forecast_type: str,
    moving_average_window: int = 30,
    forecast_horizon: int = 1,
    early_period_strategy: str = 'use_available',
    default_value: float = 0.0
) -> List[float]:
    """
    Calculate rolling forecast for multiple periods.
    
    Args:
        history: Historical values
        forecast_type: Type of forecast ('naive', 'moving_average')
        moving_average_window: Window size for moving average
        forecast_horizon: Forecast horizon
        early_period_strategy: Strategy for early period forecasting
        default_value: Default value to use if strategy is 'use_default'
        
    Returns:
        List of forecast values
    """
    if not history:
        return [default_value] * forecast_horizon
    
    # Handle early periods
    if len(history) < moving_average_window and early_period_strategy != 'use_available':
        forecast_value = handle_early_period_forecasting(
            history=history,
            strategy=early_period_strategy,
            default_value=default_value
        )
        return [forecast_value] * forecast_horizon
    
    # Generate forecast
    return generate_forecast(
        history=history,
        forecast_type=forecast_type,
        window=moving_average_window,
        horizon=forecast_horizon,
        early_period_strategy=early_period_strategy,
        default_value=default_value
    )

def calculate_forecast_error(
    forecast: Union[float, List[float]],
    actual: Union[float, List[float]]
) -> Union[float, List[float]]:
    """
    Calculate forecast error.
    
    Args:
        forecast: Forecast values
        actual: Actual values
        
    Returns:
        Forecast error
    """
    if isinstance(forecast, (int, float)) and isinstance(actual, (int, float)):
        return actual - forecast
    
    if len(forecast) != len(actual):
        raise ValueError("forecast and actual must have the same length")
    
    return [a - f for a, f in zip(actual, forecast)]

def calculate_forecast_accuracy(
    forecast: Union[float, List[float]],
    actual: Union[float, List[float]],
    metric: str = 'mape'
) -> float:
    """
    Calculate forecast accuracy.
    
    Args:
        forecast: Forecast values
        actual: Actual values
        metric: Accuracy metric ('mape', 'rmse', 'mae')
        
    Returns:
        Forecast accuracy
    """
    # Convert scalar values to lists
    if isinstance(forecast, (int, float)):
        forecast = [forecast]
    
    if isinstance(actual, (int, float)):
        actual = [actual]
    
    if len(forecast) != len(actual):
        raise ValueError("forecast and actual must have the same length")
    
    if not forecast or not actual:
        raise ValueError("forecast and actual cannot be empty")
    
    if metric == 'mape':
        # Mean Absolute Percentage Error
        mape_values = []
        for a, f in zip(actual, forecast):
            if a == 0:
                # Handle division by zero
                continue
            mape_values.append(abs((a - f) / a) * 100)
        
        if not mape_values:
            raise ZeroDivisionError("Cannot calculate MAPE with zero actual values")
        
        return sum(mape_values) / len(mape_values)
    
    elif metric == 'rmse':
        # Root Mean Square Error
        squared_errors = [(a - f) ** 2 for a, f in zip(actual, forecast)]
        return np.sqrt(sum(squared_errors) / len(squared_errors))
    
    elif metric == 'mae':
        # Mean Absolute Error
        absolute_errors = [abs(a - f) for a, f in zip(actual, forecast)]
        return sum(absolute_errors) / len(absolute_errors)
    
    else:
        raise ValueError(f"Invalid metric: {metric}")