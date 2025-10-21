import numpy as np
import tensorflow as tf
import onnxruntime as ort
from typing import Union
# ---------------------------------------

# ---------------------------------------
tf_version =int(tf.__version__.split(".", maxsplit=1)[0])
if tf_version == 1:
    from keras import Input
    from keras.models import Model, Sequential
    from keras.layers import (
        Convolution2D,
        ZeroPadding2D,
        MaxPooling2D,
        Flatten,
        Dropout,
        Activation,
    )
else:
    from tensorflow.keras import Input
    from tensorflow.keras.models import Model, Sequential
    from tensorflow.keras.layers import (
        Convolution2D,
        ZeroPadding2D,
        MaxPooling2D,
        Flatten,
        Dropout,
        Activation,
    )

# ---------------------------------------

# pylint: disable=too-few-public-methods

def base_model(input_shape=(224,224,3)) -> Model:
    input_layer = Input(shape=input_shape, name="input")
    x = ZeroPadding2D((1, 1))(input_layer)
    x = Convolution2D(64, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(64, (3, 3), activation="relu")(x)
    x = MaxPooling2D((2, 2), strides=(2, 2))(x)

    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(128, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(128, (3, 3), activation="relu")(x)
    x = MaxPooling2D((2, 2), strides=(2, 2))(x)

    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(256, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(256, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(256, (3, 3), activation="relu")(x)
    x = MaxPooling2D((2, 2), strides=(2, 2))(x)

    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = MaxPooling2D((2, 2), strides=(2, 2))(x)

    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = ZeroPadding2D((1, 1))(x)
    x = Convolution2D(512, (3, 3), activation="relu")(x)
    x = MaxPooling2D((2, 2), strides=(2, 2))(x)

    x = Convolution2D(4096, (7, 7), activation="relu")(x)
    x = Dropout(0.5)(x)
    x = Convolution2D(4096, (1, 1), activation="relu")(x)
    x = Dropout(0.5)(x)
    x = Convolution2D(2622, (1, 1))(x)
    x = Flatten()(x)
    output = Activation("softmax")(x)

    model = Model(inputs=input_layer, outputs=output)
    return model


def load_model(model_weights_path:str=None)-> Model:
    """
    Final VGG-Face model being used for finding embeddings
    Returns:
        model (Model): returning 4096 dimensional vectors
    """

    model = base_model()
    if model_weights_path is None:
        # If no path is provided, create a default directory for model weights
        raise ValueError("Model weights path must be provided")
    model.load_weights(model_weights_path)
    # 2622d dimensional model
    # vgg_face_descriptor = Model(inputs=model.layers[0].input, outputs=model.layers[-2].output)
    # 4096 dimensional model offers 6% to 14% increasement on accuracy!
    # - softmax causes underfitting
    # - added normalization layer to avoid underfitting with euclidean
    # as described here: https://github.com/serengil/deepface/issues/944
    base_model_output = Flatten()(model.layers[-5].output)
    # keras backend's l2 normalization layer troubles some gpu users (e.g. issue 957, 966)
    # base_model_output = Lambda(lambda x: K.l2_normalize(x, axis=1), name="norm_layer")(
    #     base_model_output
    # )
    vgg_face_descriptor = Model(inputs=model.input, outputs=base_model_output)
    return vgg_face_descriptor


def l2_normalize(x: tf.Tensor, axis: int = 1, epsilon: float = 1e-10) -> tf.Tensor:
    """
    L2-normalize a batch of tensors along the specified axis.
    Args:
        x (tf.Tensor): Input tensor (batch_size, ...)
        axis (int): Axis along which to normalize
        epsilon (float): Small value to avoid division by zero
    Returns:
        tf.Tensor: L2-normalized tensor
    """
    return tf.math.l2_normalize(x, axis=axis, epsilon=epsilon)


def l2_normalize_numpy(x: np.ndarray, axis: int = 1, epsilon: float = 1e-10) -> np.ndarray:
    """
    L2-normalize a batch of numpy arrays along the specified axis.
    Args:
        x (np.ndarray): Input array (batch_size, ...)
        axis (int): Axis along which to normalize
        epsilon (float): Small value to avoid division by zero
    Returns:
        np.ndarray: L2-normalized array
    """
    norm = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / (norm + epsilon)


class VggFace(tf.keras.Model):
    """
    VGG-Face model class that inherits from tf.keras.Model
    """

    def __init__(self, model_weights_path: str = None, trainable: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.face_model = load_model(model_weights_path)
        self.model_name = "VGG-Face"
        self.input_shape_size = (224, 224)
        self._output_shape = 4096
        # Make the model non-trainable by default
        self.face_model.trainable = trainable
        # Also set all layers to non-trainable if trainable is False
        if not trainable:
            for layer in self.face_model.layers:
                layer.trainable = False

    def call(self, inputs, training=None):
        """
        Forward pass of the VGG-Face model.
        This is the method called when the model is used in Keras functional API.

        Args:
            inputs: Input tensor with shape (batch_size, height, width, channels)
            training: Boolean indicating if the model is in training mode
        Returns:
            embeddings (tf.Tensor): L2-normalized embeddings with shape (batch_size, 4096)
        """
        # Convert numpy arrays to tensors if needed
        if isinstance(inputs, np.ndarray):
            inputs = tf.convert_to_tensor(inputs, dtype=tf.float32)
        
        # Ensure input is a batch
        if len(inputs.shape) == 3:
            inputs = tf.expand_dims(inputs, axis=0)
            
        # Resize if necessary
        if inputs.shape[1:3] != self.input_shape_size:
            inputs = tf.image.resize(inputs, self.input_shape_size)
        
        # Perform inference and normalization
        embedding = self.face_model(inputs, training=training)
        embedding = l2_normalize(embedding)
        
        # Ensure output shape is (batch, 4096)
        if len(embedding.shape) == 3 and embedding.shape[1] == 1:
            embedding = tf.squeeze(embedding, axis=1)
        if len(embedding.shape) == 1:
            embedding = tf.expand_dims(embedding, axis=0)
            
        return embedding

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """
        Make the VggFace instance callable.
        This allows using the instance like: vgg_face(img)
        
        Args:
            img (np.ndarray): pre-loaded batch of images
        Returns:
            embeddings (np.ndarray): multi-dimensional array with L2-normalized embeddings
        """
        return self.predict(img)

    def predict(self, img: np.ndarray) -> np.ndarray:
        """
        Generates embeddings using the VGG-Face model.
        This method now supports batch data and returns results as numpy arrays.

        Args:
            img (np.ndarray): pre-loaded batch of images
        Returns:
            embeddings (np.ndarray): multi-dimensional array with L2-normalized embeddings
        """
        tensor_result = self.call(img, training=False)
        return tensor_result.numpy()

    def get_config(self):
        """Return the config of the model for serialization."""
        config = super().get_config()
        config.update({
            'model_name': self.model_name,
            'output_shape': self._output_shape,
        })
        return config


class VggFace_onnx:
    """
    VGG-Face ONNX model class for fast inference using ONNX Runtime
    """

    def __init__(self, onnx_model_path: str = None, providers: list = None):
        """
        Initialize VggFace ONNX model.
        
        Args:
            onnx_model_path (str): Path to the ONNX model file
            providers (list): List of execution providers (e.g., ['CUDAExecutionProvider', 'CPUExecutionProvider'])
        """
        if onnx_model_path is None:
            raise ValueError("ONNX model path must be provided.")
            
        if providers is None:
            # Try CUDA first, fallback to CPU
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        
        # Set session options for optimization
        self.session_options = ort.SessionOptions()
        self.session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session_options.enable_mem_pattern = True
        self.session_options.enable_cpu_mem_arena = True
        self.session_options.intra_op_num_threads = 4
        
        # Add memory management options for CUDA
        self.session_options.add_session_config_entry("memory.enable_memory_arena_shrinkage", "")
        
        # Create ONNX Runtime session
        try:
            self.session = ort.InferenceSession(
                onnx_model_path, 
                sess_options=self.session_options, 
                providers=providers
            )
        except Exception as e:
            print(f"Failed to create session with GPU providers, falling back to CPU: {e}")
            # Fallback to CPU only
            self.session = ort.InferenceSession(
                onnx_model_path, 
                sess_options=self.session_options, 
                providers=["CPUExecutionProvider"]
            )
        
        # Get model info
        self.input_names = [input.name for input in self.session.get_inputs()]
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        # Model properties
        self.model_name = "VGG-Face-ONNX"
        self.input_shape_size = (224, 224)
        self._output_shape = 4096
        
        print(f"ONNX model loaded with providers: {self.session.get_providers()}")
        print(f"Input names: {self.input_names}")
        print(f"Output names: {self.output_names}")

    def __call__(self, img: np.ndarray) -> np.ndarray:
        """
        Make the VggFace_onnx instance callable.
        This allows using the instance like: vgg_face_onnx(img)
        
        Args:
            img (np.ndarray): pre-loaded batch of images
        Returns:
            embeddings (np.ndarray): multi-dimensional array
        """
        return self.predict(img)

    def _preprocess_input(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess input images for ONNX inference.
        
        Args:
            img (np.ndarray): Input images
        Returns:
            np.ndarray: Preprocessed images
        """
        # Convert to float32 if needed
        if img.dtype != np.float32:
            img = img.astype(np.float32)
        
        # Ensure input is a batch
        if len(img.shape) == 3:
            img = np.expand_dims(img, axis=0)
        
        # Resize if necessary
        if img.shape[1:3] != self.input_shape_size:
            # Simple resize using numpy (for ONNX compatibility)
            batch_size = img.shape[0]
            channels = img.shape[3]
            resized_batch = np.zeros((batch_size, *self.input_shape_size, channels), dtype=np.float32)
            
            for i in range(batch_size):
                # Use TensorFlow for resizing if available, otherwise skip resize
                try:
                    import cv2
                    resized_batch[i] = cv2.resize(img[i], self.input_shape_size, interpolation=cv2.INTER_LINEAR)
                except ImportError:
                    if img.shape[1:3] == self.input_shape_size:
                        resized_batch[i] = img[i]
                    else:
                        # If no resize library available and sizes don't match, raise error
                        raise ValueError(f"Input shape {img.shape[1:3]} doesn't match required {self.input_shape_size}. Install cv2 for automatic resizing.")
            
            img = resized_batch
        
        return img

    def predict(self, img: np.ndarray) -> np.ndarray:
        """
        Generates embeddings using the VGG-Face ONNX model.
        This method supports batch data and returns results as numpy arrays.

        Args:
            img (np.ndarray): pre-loaded batch of images with shape (batch_size, height, width, channels)
        Returns:
            embeddings (np.ndarray): L2-normalized embeddings with shape (batch_size, 4096)
        """
        # Preprocess input
        img_processed = self._preprocess_input(img)
        
        # Prepare input dictionary for ONNX Runtime
        inputs = {self.input_names[0]: img_processed}
        
        # Run inference
        outputs = self.session.run(self.output_names, inputs)
        embedding = outputs[0]  # Get the first (and likely only) output
        
        # Apply L2 normalization
        embedding = l2_normalize_numpy(embedding)
        
        # Ensure output shape is (batch, 4096)
        if len(embedding.shape) == 3 and embedding.shape[1] == 1:
            embedding = np.squeeze(embedding, axis=1)
        if len(embedding.shape) == 1:
            embedding = np.expand_dims(embedding, axis=0)
        
        return embedding

    def get_model_info(self):
        """
        Get information about the ONNX model.
        
        Returns:
            dict: Model information including input/output shapes and provider info
        """
        input_info = []
        for inp in self.session.get_inputs():
            input_info.append({
                'name': inp.name,
                'shape': inp.shape,
                'type': inp.type
            })
        
        output_info = []
        for out in self.session.get_outputs():
            output_info.append({
                'name': out.name,
                'shape': out.shape,
                'type': out.type
            })
        
        return {
            'model_name': self.model_name,
            'providers': self.session.get_providers(),
            'inputs': input_info,
            'outputs': output_info
        }
