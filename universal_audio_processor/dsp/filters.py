# dsp/filters.py
import numpy as np

class LMSFilter:
    """Least Mean Squares adaptive filter"""
    
    def __init__(self, filter_length=256, mu=0.01):
        """
        Args:
            filter_length: Number of filter taps
            mu: Step size (learning rate)
        """
        self.filter_length = filter_length
        self.mu = mu
        self.weights = np.zeros(filter_length)
        self.input_buffer = np.zeros(filter_length)
    
    def update(self, desired, reference):
        """
        Update filter weights
        
        Args:
            desired: Desired signal (noisy speech)
            reference: Reference signal (noise)
        """
        # Shift input buffer
        self.input_buffer = np.roll(self.input_buffer, 1)
        self.input_buffer[0] = reference
        
        # Filter output
        output = np.dot(self.weights, self.input_buffer)
        
        # Error
        error = desired - output
        
        # Update weights
        self.weights += 2 * self.mu * error * self.input_buffer
        
        return error
    
    def filter(self, signal_sequence, noise_sequence):
        """Filter entire sequence"""
        output = np.zeros(len(signal_sequence))
        
        for i in range(len(signal_sequence)):
            output[i] = self.update(signal_sequence[i], noise_sequence[i])
        
        return output
    
    def reset(self):
        """Reset filter state"""
        self.weights.fill(0)
        self.input_buffer.fill(0)


class NLMSFilter:
    """Normalized Least Mean Squares adaptive filter"""
    
    def __init__(self, filter_length=256, mu=0.5, epsilon=1e-6):
        """
        Args:
            filter_length: Number of filter taps
            mu: Step size (0 < mu < 2 for stability)
            epsilon: Small constant to avoid division by zero
        """
        self.filter_length = filter_length
        self.mu = mu
        self.epsilon = epsilon
        self.weights = np.zeros(filter_length)
        self.input_buffer = np.zeros(filter_length)
    
    def update(self, desired, reference):
        """Update filter weights (normalized)"""
        # Shift input buffer
        self.input_buffer = np.roll(self.input_buffer, 1)
        self.input_buffer[0] = reference
        
        # Filter output
        output = np.dot(self.weights, self.input_buffer)
        
        # Error
        error = desired - output
        
        # Normalized step size
        input_power = np.dot(self.input_buffer, self.input_buffer)
        normalized_mu = self.mu / (input_power + self.epsilon)
        
        # Update weights
        self.weights += normalized_mu * error * self.input_buffer
        
        return error
    
    def filter(self, signal_sequence, noise_sequence):
        """Filter entire sequence"""
        output = np.zeros(len(signal_sequence))
        
        for i in range(len(signal_sequence)):
            output[i] = self.update(signal_sequence[i], noise_sequence[i])
        
        return output
    
    def reset(self):
        """Reset filter state"""
        self.weights.fill(0)
        self.input_buffer.fill(0)


class RLSFilter:
    """Recursive Least Squares adaptive filter"""
    
    def __init__(self, filter_length=256, forgetting_factor=0.99, delta=1.0):
        """
        Args:
            filter_length: Number of filter taps
            forgetting_factor: Lambda (0 < lambda <= 1)
            delta: Initialization parameter
        """
        self.filter_length = filter_length
        self.lambda_factor = forgetting_factor
        self.weights = np.zeros(filter_length)
        self.P = np.eye(filter_length) / delta  # Inverse correlation matrix
        self.input_buffer = np.zeros(filter_length)
    
    def update(self, desired, reference):
        """Update filter weights using RLS"""
        # Shift input buffer
        self.input_buffer = np.roll(self.input_buffer, 1)
        self.input_buffer[0] = reference
        
        # Filter output
        output = np.dot(self.weights, self.input_buffer)
        
        # Error
        error = desired - output
        
        # Gain vector
        pi = np.dot(self.P, self.input_buffer)
        k = pi / (self.lambda_factor + np.dot(self.input_buffer, pi))
        
        # Update weights
        self.weights += k * error
        
        # Update inverse correlation matrix
        self.P = (self.P - np.outer(k, pi)) / self.lambda_factor
        
        return error
    
    def filter(self, signal_sequence, noise_sequence):
        """Filter entire sequence"""
        output = np.zeros(len(signal_sequence))
        
        for i in range(len(signal_sequence)):
            output[i] = self.update(signal_sequence[i], noise_sequence[i])
        
        return output
    
    def reset(self):
        """Reset filter state"""
        self.weights.fill(0)
        self.P = np.eye(self.filter_length)
        self.input_buffer.fill(0)


class KalmanFilter:
    """Kalman filter for speech enhancement"""
    
    def __init__(self, order=10, process_noise=1e-4, measurement_noise=1e-2):
        """
        Args:
            order: Filter order (state dimension)
            process_noise: Process noise variance
            measurement_noise: Measurement noise variance
        """
        self.order = order
        
        # State estimate
        self.x = np.zeros(order)
        
        # Error covariance
        self.P = np.eye(order)
        
        # Process noise covariance
        self.Q = np.eye(order) * process_noise
        
        # Measurement noise covariance
        self.R = measurement_noise
        
        # State transition matrix (AR model)
        self.F = np.eye(order)
        
        # Observation matrix
        self.H = np.zeros(order)
        self.H[0] = 1.0
    
    def update(self, measurement):
        """Kalman filter update step"""
        # Prediction
        x_pred = np.dot(self.F, self.x)
        P_pred = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        
        # Innovation
        y = measurement - np.dot(self.H, x_pred)
        S = np.dot(np.dot(self.H, P_pred), self.H.T) + self.R
        
        # Kalman gain
        K = np.dot(np.dot(P_pred, self.H.T), 1.0 / S)
        
        # Update
        self.x = x_pred + K * y
        self.P = P_pred - np.outer(K, np.dot(self.H, P_pred))
        
        return self.x[0]
    
    def filter(self, signal):
        """Filter signal"""
        output = np.zeros(len(signal))
        
        for i in range(len(signal)):
            output[i] = self.update(signal[i])
        
        return output
    
    def reset(self):
        """Reset filter state"""
        self.x.fill(0)
        self.P = np.eye(self.order)