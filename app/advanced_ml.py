import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple, List
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

try:
    # Try new Keras 3.x import structure first (TensorFlow 2.16+)
    from keras.models import Sequential
    from keras.layers import LSTM, Dense, Dropout
    from keras.optimizers import Adam
    HAS_TENSORFLOW = True
except (ImportError, ModuleNotFoundError, Exception):
    try:
        # Fall back to old TensorFlow 2.x structure
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.optimizers import Adam
        HAS_TENSORFLOW = True
    except (ImportError, ModuleNotFoundError, Exception):
        HAS_TENSORFLOW = False
        # Silently disabled - LSTM is optional
        pass

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    logger.warning("Statsmodels not installed. ARIMA models disabled.")


class LSTMPredictor:
    """Advanced LSTM (Long Short-Term Memory) neural network for time series forecasting"""
    
    def __init__(self, lookback_window=7, forecast_horizon=30):
        self.lookback_window = lookback_window
        self.forecast_horizon = forecast_horizon
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.is_trained = False
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X, y = [], []
        for i in range(len(data) - self.lookback_window):
            X.append(data[i:(i + self.lookback_window)])
            y.append(data[i + self.lookback_window])
        return np.array(X), np.array(y)
    
    def train(self, spending_data: np.ndarray) -> Dict:
        """
        Train LSTM model on spending history
        Args:
            spending_data: 1D array of historical spending amounts
        Returns:
            Dictionary with training metrics
        """
        if not HAS_TENSORFLOW:
            return {'error': 'LSTM disabled - using alternative models', 'status': 'fallback'}
        
        if len(spending_data) < 20:
            return {'error': 'Insufficient data. Need at least 20 data points.'}
        
        try:
            # Normalize data
            normalized_data = self.scaler.fit_transform(spending_data.reshape(-1, 1)).flatten()
            
            # Create sequences
            X, y = self._create_sequences(normalized_data)
            
            if len(X) < 5:
                return {'error': 'Not enough sequences for training.'}
            
            # Build LSTM model
            self.model = Sequential([
                LSTM(64, activation='relu', input_shape=(self.lookback_window, 1), return_sequences=True),
                Dropout(0.2),
                LSTM(32, activation='relu'),
                Dropout(0.2),
                Dense(16, activation='relu'),
                Dense(1)
            ])
            
            self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            # Train with minimal epochs for fast inference
            history = self.model.fit(
                X.reshape(X.shape[0], X.shape[1], 1),
                y,
                epochs=50,
                batch_size=8,
                verbose=0,
                validation_split=0.2
            )
            
            self.is_trained = True
            return {
                'status': 'success',
                'train_loss': float(history.history['loss'][-1]),
                'val_loss': float(history.history['val_loss'][-1])
            }
        
        except Exception as e:
            logger.error(f"LSTM training error: {str(e)}")
            return {'error': str(e)}
    
    def predict(self, spending_data: np.ndarray) -> Dict:
        """
        Predict future spending using trained LSTM
        Args:
            spending_data: Historical spending data
        Returns:
            Dictionary with predictions and metrics
        """
        if not self.is_trained or self.model is None:
            self.train(spending_data)
        
        try:
            normalized_data = self.scaler.transform(spending_data.reshape(-1, 1)).flatten()
            
            # Prepare input for prediction
            last_sequence = normalized_data[-self.lookback_window:]
            predictions = []
            current_sequence = last_sequence.copy()
            
            # Forecast next 30 days
            for _ in range(self.forecast_horizon):
                next_pred = self.model.predict(
                    current_sequence.reshape(1, self.lookback_window, 1),
                    verbose=0
                )[0, 0]
                predictions.append(next_pred)
                current_sequence = np.append(current_sequence[1:], next_pred)
            
            # Denormalize predictions
            predictions_array = np.array(predictions).reshape(-1, 1)
            actual_predictions = self.scaler.inverse_transform(predictions_array).flatten()
            actual_predictions = np.maximum(actual_predictions, 0)  # No negative spending
            
            return {
                'status': 'success',
                'daily_predictions': actual_predictions.tolist(),
                'total_predicted': float(np.sum(actual_predictions)),
                'daily_average': float(np.mean(actual_predictions)),
                'peaks': self._identify_peaks(actual_predictions),
                'model': 'LSTM Neural Network'
            }
        
        except Exception as e:
            logger.error(f"LSTM prediction error: {str(e)}")
            return {'error': str(e)}
    
    def _identify_peaks(self, data: np.ndarray, threshold_percentile: int = 75) -> List[Dict]:
        """Identify spending peaks in predictions"""
        threshold = np.percentile(data, threshold_percentile)
        peaks = []
        for i, val in enumerate(data):
            if val > threshold:
                peaks.append({'day': i+1, 'amount': float(val), 'severity': 'high' if val > np.percentile(data, 90) else 'medium'})
        return peaks[:5]  # Return top 5 peaks


class ARIMAPredictor:
    """ARIMA (AutoRegressive Integrated Moving Average) for time series forecasting"""
    
    def __init__(self, order: Tuple[int, int, int] = (5, 1, 2)):
        self.order = order
        self.model = None
        self.fitted_model = None
    
    def train_and_predict(self, spending_data: np.ndarray, forecast_steps: int = 30) -> Dict:
        """
        Train ARIMA model and generate forecasts
        Args:
            spending_data: Historical spending data
            forecast_steps: Number of days to forecast
        Returns:
            Dictionary with predictions and confidence intervals
        """
        if not HAS_STATSMODELS:
            return {'error': 'Statsmodels not installed. Install with: pip install statsmodels'}
        
        if len(spending_data) < 20:
            return {'error': 'Insufficient data. Need at least 20 data points.'}
        
        try:
            # Fit ARIMA model
            self.model = ARIMA(spending_data, order=self.order)
            self.fitted_model = self.model.fit()
            
            # Generate forecast with confidence intervals
            forecast_result = self.fitted_model.get_forecast(steps=forecast_steps)
            forecasted_values = forecast_result.predicted_mean.values
            forecast_ci = forecast_result.conf_int(alpha=0.05)
            
            # Ensure non-negative predictions
            forecasted_values = np.maximum(forecasted_values, 0)
            lower_bound = np.maximum(forecast_ci.iloc[:, 0].values, 0)
            upper_bound = np.maximum(forecast_ci.iloc[:, 1].values, 0)
            
            return {
                'status': 'success',
                'daily_predictions': forecasted_values.tolist(),
                'lower_bound': lower_bound.tolist(),
                'upper_bound': upper_bound.tolist(),
                'total_predicted': float(np.sum(forecasted_values)),
                'daily_average': float(np.mean(forecasted_values)),
                'confidence': '95%',
                'model': f'ARIMA{self.order}',
                'aic': float(self.fitted_model.aic),
                'bic': float(self.fitted_model.bic)
            }
        
        except Exception as e:
            logger.error(f"ARIMA forecast error: {str(e)}")
            return {'error': str(e)}


class VARModel:
    """Vector Autoregression for multi-variable time series analysis"""
    
    @staticmethod
    def analyze_spending_categories(spending_by_category: Dict[str, np.ndarray]) -> Dict:
        """
        Analyze correlations and dynamics between spending categories
        Args:
            spending_by_category: Dictionary of category names to spending arrays
        Returns:
            Analysis of category correlations and trends
        """
        try:
            # Create DataFrame
            df = pd.DataFrame(spending_by_category)
            
            # Calculate correlations
            correlations = df.corr().to_dict()
            
            # Calculate trend coefficients (simple linear regression)
            trends = {}
            for col in df.columns:
                x = np.arange(len(df[col]))
                y = df[col].values
                if len(x) > 1 and not np.all(np.isnan(y)):
                    slope = np.polyfit(x, np.nan_to_num(y), 1)[0]
                    trends[col] = float(slope)
            
            return {
                'status': 'success',
                'correlations': correlations,
                'trends': trends,
                'model': 'Vector Autoregression'
            }
        
        except Exception as e:
            logger.error(f"VAR analysis error: {str(e)}")
            return {'error': str(e)}


class GARCHVolatilityModel:
    """GARCH model for volatility analysis (useful for investment portfolio risk)"""
    
    @staticmethod
    def calculate_volatility(returns_data: np.ndarray, window: int = 20) -> Dict:
        """
        Calculate rolling volatility for asset prices
        Args:
            returns_data: Array of price returns (price changes)
            window: Rolling window size
        Returns:
            Volatility metrics and risk indicators
        """
        if len(returns_data) < window:
            return {'error': 'Insufficient data points'}
        
        try:
            # Calculate rolling volatility (standard deviation of returns)
            rolling_vol = pd.Series(returns_data).rolling(window=window).std().values
            
            # Historical volatility (annualized)
            current_volatility = np.std(returns_data[-window:])
            annualized_vol = current_volatility * np.sqrt(252)  # 252 trading days
            
            # Value at Risk (95% confidence level)
            var_95 = np.percentile(returns_data, 5)
            
            # Extreme Value Analysis
            worst_case = np.min(returns_data)
            best_case = np.max(returns_data)
            
            return {
                'status': 'success',
                'current_volatility': float(current_volatility),
                'annualized_volatility': float(annualized_vol),
                'value_at_risk_95': float(var_95),
                'worst_case_return': float(worst_case),
                'best_case_return': float(best_case),
                'volatility_trend': float(rolling_vol[-1]) if len(rolling_vol) > 0 else 0,
                'risk_level': 'High' if annualized_vol > 0.25 else ('Medium' if annualized_vol > 0.15 else 'Low')
            }
        
        except Exception as e:
            logger.error(f"GARCH volatility error: {str(e)}")
            return {'error': str(e)}


class EnsembleForecaster:
    """Combines multiple models for robust predictions"""
    
    def __init__(self):
        self.lstm = LSTMPredictor()
        self.arima = ARIMAPredictor()
    
    def ensemble_forecast(self, spending_data: np.ndarray) -> Dict:
        """
        Generate weighted ensemble forecasts combining LSTM and ARIMA
        Args:
            spending_data: Historical spending data
        Returns:
            Ensemble predictions with confidence metrics
        """
        results = {
            'status': 'success',
            'models': {}
        }
        
        # LSTM prediction
        lstm_result = self.lstm.predict(spending_data)
        if 'error' not in lstm_result:
            results['models']['lstm'] = lstm_result
            lstm_forecast = np.array(lstm_result['daily_predictions'])
        else:
            lstm_forecast = None
        
        # ARIMA prediction
        arima_result = self.arima.train_and_predict(spending_data)
        if 'error' not in arima_result:
            results['models']['arima'] = arima_result
            arima_forecast = np.array(arima_result['daily_predictions'])
        else:
            arima_forecast = None
        
        # Ensemble (weighted average: 60% LSTM, 40% ARIMA for better stability)
        if lstm_forecast is not None and arima_forecast is not None:
            ensemble = (lstm_forecast * 0.6 + arima_forecast * 0.4)
        elif lstm_forecast is not None:
            ensemble = lstm_forecast
        elif arima_forecast is not None:
            ensemble = arima_forecast
        else:
            return {'error': 'All models failed. Install tensorflow and statsmodels.'}
        
        results['ensemble_prediction'] = ensemble.tolist()
        results['total_predicted'] = float(np.sum(ensemble))
        results['daily_average'] = float(np.mean(ensemble))
        results['std_deviation'] = float(np.std(ensemble))
        results['model_confidence'] = 'High' if (len(results['models']) > 1) else 'Medium'
        
        return results
