"""
Models module
"""

import os

import torch

from transformers import AutoModel, AutoModelForQuestionAnswering, AutoModelForSeq2SeqLM, AutoModelForSequenceClassification

from .onnx import OnnxModel


class Models:
    """
    Utility methods for working with machine learning models
    """

    @staticmethod
    def checklength(config, tokenizer):
        """
        Checks the length for a Hugging Face Transformers tokenizer using a Hugging Face Transformers config. Copies the
        max_position_embeddings parameter if the tokenizer has no max_length set. This helps with backwards compatibility
        with older tokenizers.

        Args:
            config: transformers config
            tokenizer: transformers tokenizer
        """

        # Unpack nested config, handles passing model directly
        if hasattr(config, "config"):
            config = config.config

        if (
            hasattr(config, "max_position_embeddings")
            and tokenizer
            and hasattr(tokenizer, "model_max_length")
            and tokenizer.model_max_length == int(1e30)
        ):
            tokenizer.model_max_length = config.max_position_embeddings

    @staticmethod
    def maxlength(config, tokenizer):
        """
        Gets the best max length to use for generate calls. This method will return config.max_length if it's set. Otherwise, it will return
        tokenizer.model_max_length.

        Args:
            config: transformers config
            tokenizer: transformers tokenizer
        """

        # Unpack nested config, handles passing model directly
        if hasattr(config, "config"):
            config = config.config

        # Get non-defaulted fields
        keys = config.to_diff_dict()

        # Use config.max_length if not set to default value, else use tokenizer.model_max_length if available
        return config.max_length if "max_length" in keys or not hasattr(tokenizer, "model_max_length") else tokenizer.model_max_length

    @staticmethod
    def deviceid(gpu):
        """
        Translates input gpu argument into a device id.

        Args:
            gpu: True/False if GPU should be enabled, also supports a device id/string/instance

        Returns:
            device id
        """

        # Return if this is already a torch device
        # pylint: disable=E1101
        if isinstance(gpu, torch.device):
            return gpu

        # Always return -1 if gpu is None or an accelerator device is unavailable
        if gpu is None or not Models.hasaccelerator():
            return -1

        # Default to device 0 if gpu is True and not otherwise specified
        if isinstance(gpu, bool):
            return 0 if gpu else -1

        # Return gpu as device id if gpu flag is an int
        return int(gpu)

    @staticmethod
    def device(deviceid):
        """
        Gets a tensor device.

        Args:
            deviceid: device id

        Returns:
            tensor device
        """

        # Torch device
        # pylint: disable=E1101
        return deviceid if isinstance(deviceid, torch.device) else torch.device(Models.reference(deviceid))

    @staticmethod
    def reference(deviceid):
        """
        Gets a tensor device reference.

        Args:
            deviceid: device id

        Returns:
            device reference
        """

        return (
            deviceid
            if isinstance(deviceid, str)
            else "cpu"
            if deviceid < 0
            else f"cuda:{deviceid}"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else Models.finddevice()
        )

    @staticmethod
    def hasaccelerator():
        """
        Checks if there is an accelerator device available.

        Returns:
            True if an accelerator device is available, False otherwise
        """

        return torch.cuda.is_available() or torch.backends.mps.is_available() or bool(Models.finddevice())

    @staticmethod
    def finddevice():
        """
        Attempts to find an alternative accelerator device.

        Returns:
            name of first alternative accelerator available or None if not found
        """

        return next((device for device in ["xpu"] if hasattr(torch, device) and getattr(torch, device).is_available()), None)

    @staticmethod
    def load(path, config=None, task="default"):
        """
        Loads a machine learning model. Handles multiple model frameworks (ONNX, Transformers).

        Args:
            path: path to model
            config: path to model configuration
            task: task name used to lookup model type

        Returns:
            machine learning model
        """

        # Detect ONNX models
        if isinstance(path, bytes) or (isinstance(path, str) and os.path.isfile(path)):
            return OnnxModel(path, config)

        # Return path, if path isn't a string
        if not isinstance(path, str):
            return path

        # Transformer models
        models = {
            "default": AutoModel.from_pretrained,
            "question-answering": AutoModelForQuestionAnswering.from_pretrained,
            "summarization": AutoModelForSeq2SeqLM.from_pretrained,
            "text-classification": AutoModelForSequenceClassification.from_pretrained,
            "zero-shot-classification": AutoModelForSequenceClassification.from_pretrained,
        }

        # Load model for supported tasks. Return path for unsupported tasks.
        return models[task](path) if task in models else path
