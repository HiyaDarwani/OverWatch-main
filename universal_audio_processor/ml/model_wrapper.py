# ml/model_wrapper.py
import numpy as np
import logging

logger = logging.getLogger(__name__)

class UniversalModelWrapper:
    """Universal wrapper for PyTorch, ONNX, TFLite models"""
    
    def __init__(self, model_path, model_type='auto'):
        """
        Args:
            model_path: Path to model file
            model_type: 'pytorch', 'onnx', 'tflite', or 'auto'
        """
        self.model_path = model_path
        self.model = None
        self.session = None
        self.interpreter = None
        
        # Auto-detect model type
        if model_type == 'auto':
            if model_path.endswith('.pth') or model_path.endswith('.pt'):
                model_type = 'pytorch'
            elif model_path.endswith('.onnx'):
                model_type = 'onnx'
            elif model_path.endswith('.tflite'):
                model_type = 'tflite'
            else:
                raise ValueError(f"Cannot auto-detect model type from {model_path}")
        
        self.model_type = model_type
        
        # Load model
        self._load_model()
    
    def _load_model(self):
        """Load model based on type"""
        if self.model_type == 'pytorch':
            self._load_pytorch()
        elif self.model_type == 'onnx':
            self._load_onnx()
        elif self.model_type == 'tflite':
            self._load_tflite()
    
    def _load_pytorch(self):
        """Load PyTorch model"""
        try:
            import torch
            
            # Load checkpoint
            checkpoint = torch.load(self.model_path, map_location='cpu')
            
            # Check if it's a state dict or full model
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                # Need to instantiate model first (architecture-specific)
                logger.warning("State dict found. Model architecture must be provided separately.")
                self.model = checkpoint
            else:
                self.model = checkpoint
            
            self.model.eval()
            
            # Detect device
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            if hasattr(self.model, 'to'):
                self.model.to(self.device)
            
            logger.info(f"Loaded PyTorch model on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            raise
    
    def _load_onnx(self):
        """Load ONNX model"""
        try:
            import onnxruntime as ort
            
            # Session options
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Providers (GPU if available)
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers
            )
            
            # Get input/output info
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            
            logger.info(f"Loaded ONNX model (input: {self.input_name}, output: {self.output_name})")
            
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise
    
    def _load_tflite(self):
        """Load TFLite model"""
        try:
            import tensorflow as tf
            
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input/output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info(f"Loaded TFLite model")
            
        except Exception as e:
            logger.error(f"Failed to load TFLite model: {e}")
            raise
    
    def predict(self, input_data):
        """
        Run inference
        
        Args:
            input_data: numpy array
        
        Returns:
            numpy array
        """
        if self.model_type == 'pytorch':
            return self._predict_pytorch(input_data)
        elif self.model_type == 'onnx':
            return self._predict_onnx(input_data)
        elif self.model_type == 'tflite':
            return self._predict_tflite(input_data)
    
    def _predict_pytorch(self, input_data):
        """PyTorch inference"""
        import torch
        
        with torch.no_grad():
            # Convert to tensor
            input_tensor = torch.from_numpy(input_data).float()
            
            if hasattr(self.model, 'to'):
                input_tensor = input_tensor.to(self.device)
            
            # Inference
            if callable(self.model):
                output = self.model(input_tensor)
            else:
                # State dict only - cannot run inference
                raise ValueError("Model is a state dict. Need architecture.")
            
            # Convert back to numpy
            if hasattr(output, 'cpu'):
                return output.cpu().numpy()
            else:
                return output
    
    def _predict_onnx(self, input_data):
        """ONNX inference"""
        # Ensure float32
        input_data = input_data.astype(np.float32)
        
        # Run inference
        output = self.session.run(
            [self.output_name],
            {self.input_name: input_data}
        )
        
        return output[0]
    
    def _predict_tflite(self, input_data):
        """TFLite inference"""
        # Set input tensor
        self.interpreter.set_tensor(
            self.input_details[0]['index'],
            input_data.astype(np.float32)
        )
        
        # Run inference
        self.interpreter.invoke()
        
        # Get output
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        return output
    
    def get_input_shape(self):
        """Get expected input shape"""
        if self.model_type == 'onnx':
            return self.session.get_inputs()[0].shape
        elif self.model_type == 'tflite':
            return self.input_details[0]['shape']
        else:
            return None
    
    def get_output_shape(self):
        """Get output shape"""
        if self.model_type == 'onnx':
            return self.session.get_outputs()[0].shape
        elif self.model_type == 'tflite':
            return self.output_details[0]['shape']
        else:
            return None


class ModelOptimizer:
    """Optimize models for deployment"""
    
    @staticmethod
    def pytorch_to_onnx(model, dummy_input, output_path, opset_version=14):
        """Convert PyTorch to ONNX"""
        import torch
        
        model.eval()
        
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        
        logger.info(f"Exported PyTorch model to ONNX: {output_path}")
    
    @staticmethod
    def quantize_onnx(model_path, output_path, calibration_data=None):
        """Quantize ONNX model to INT8"""
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        quantize_dynamic(
            model_input=model_path,
            model_output=output_path,
            weight_type=QuantType.QUInt8
        )
        
        logger.info(f"Quantized ONNX model saved to: {output_path}")
    
    @staticmethod
    def pytorch_to_tflite(model, dummy_input, output_path):
        """Convert PyTorch to TFLite (via ONNX)"""
        import torch
        import onnx
        from onnx_tf.backend import prepare
        import tensorflow as tf
        
        # PyTorch -> ONNX
        onnx_path = output_path.replace('.tflite', '.onnx')
        ModelOptimizer.pytorch_to_onnx(model, dummy_input, onnx_path)
        
        # ONNX -> TF
        onnx_model = onnx.load(onnx_path)
        tf_rep = prepare(onnx_model)
        
        # TF -> TFLite
        converter = tf.lite.TFLiteConverter.from_saved_model(tf_rep.export_graph())
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        logger.info(f"Converted to TFLite: {output_path}")