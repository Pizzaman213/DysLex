"""Quick Correction Service using ONNX Runtime.

Provides fast local corrections for common dyslexic errors using
an ONNX-optimized DistilBERT model. Target: <50ms latency.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from app.models.correction import Correction, Position

logger = logging.getLogger(__name__)


class QuickCorrectionService:
    """ONNX-based quick correction service."""

    def __init__(
        self,
        model_path: str | Path,
        cache_ttl: int = 60,
    ):
        """Initialize the service.

        Args:
            model_path: Path to ONNX model directory
            cache_ttl: Cache time-to-live in seconds
        """
        self.model_path = Path(model_path)
        self.cache_ttl = cache_ttl
        self.cache: dict[str, tuple[list[Correction], float]] = {}

        # Load base model
        logger.info(f"Loading ONNX model from {self.model_path}...")
        self.base_session = self._load_session(self.model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))

        # User-specific sessions (for personalized adapters)
        self.user_sessions: dict[str, ort.InferenceSession] = {}

        logger.info("QuickCorrectionService initialized")

    def _load_session(self, model_path: Path) -> ort.InferenceSession:
        """Load ONNX inference session.

        Args:
            model_path: Path to model directory

        Returns:
            ONNX InferenceSession
        """
        onnx_file = model_path / "model.onnx"

        if not onnx_file.exists():
            raise FileNotFoundError(f"ONNX model not found: {onnx_file}")

        return ort.InferenceSession(
            str(onnx_file),
            providers=["CPUExecutionProvider"],
        )

    def _get_cache_key(self, text: str, user_id: str) -> str:
        """Generate cache key for text and user.

        Args:
            text: Input text
            user_id: User ID

        Returns:
            Cache key hash
        """
        return hashlib.md5(f"{user_id}:{text}".encode()).hexdigest()

    def _decode_predictions(
        self,
        text: str,
        predictions: np.ndarray,
        tokens: list[str],
        offset_mapping: list[tuple[int, int]],
    ) -> list[Correction]:
        """Decode model predictions into Correction objects.

        Args:
            text: Original input text
            predictions: Model output logits
            tokens: Tokenized text
            offset_mapping: Character offsets for each token

        Returns:
            List of corrections
        """
        corrections = []

        # Get predicted labels
        predicted_labels = np.argmax(predictions, axis=-1)[0]
        confidences = np.max(predictions, axis=-1)[0]

        # Find error tokens
        current_error = None
        error_tokens = []
        error_offsets = []
        error_confidences = []

        for i, (label, token, offset, confidence) in enumerate(
            zip(predicted_labels, tokens, offset_mapping, confidences)
        ):
            # Skip special tokens
            if token in ["[CLS]", "[SEP]", "[PAD]"]:
                continue

            if label != 0:  # Error detected
                if current_error is None:
                    # Start new error
                    current_error = token
                    error_tokens = [token]
                    error_offsets = [offset]
                    error_confidences = [confidence]
                else:
                    # Continue error
                    error_tokens.append(token)
                    error_offsets.append(offset)
                    error_confidences.append(confidence)
            else:
                # No error or end of error
                if current_error is not None:
                    # Process completed error
                    correction = self._create_correction(
                        text,
                        error_tokens,
                        error_offsets,
                        error_confidences,
                    )
                    if correction:
                        corrections.append(correction)

                    # Reset
                    current_error = None
                    error_tokens = []
                    error_offsets = []
                    error_confidences = []

        # Handle error at end of text
        if current_error is not None:
            correction = self._create_correction(
                text,
                error_tokens,
                error_offsets,
                error_confidences,
            )
            if correction:
                corrections.append(correction)

        return corrections

    def _create_correction(
        self,
        text: str,
        tokens: list[str],
        offsets: list[tuple[int, int]],
        confidences: list[float],
    ) -> Correction | None:
        """Create Correction object from error tokens.

        Args:
            text: Original text
            tokens: Error tokens
            offsets: Character offsets
            confidences: Confidence scores

        Returns:
            Correction object or None
        """
        if not tokens or not offsets:
            return None

        # Get position in text
        start = offsets[0][0]
        end = offsets[-1][1]
        original = text[start:end]

        # Reconstruct word from tokens (remove ## for wordpiece)
        word = "".join(t.replace("##", "") for t in tokens)

        # Simple correction logic (can be improved)
        corrected = self._simple_correct(word)

        if corrected == word:
            # No correction found
            return None

        # Average confidence
        avg_confidence = float(np.mean(confidences))

        return Correction(
            original=original,
            correction=corrected,
            position=Position(start=start, end=end),
            confidence=avg_confidence,
            error_type="quick",  # Type can be refined
            explanation=f"Detected common error: {original} → {corrected}",
        )

    def _simple_correct(self, word: str) -> str:
        """Apply simple correction rules.

        This is a basic implementation. In production, this could:
        - Use a confusion pair dictionary
        - Apply learned patterns from user profile
        - Use edit distance with known words

        Args:
            word: Misspelled word

        Returns:
            Corrected word
        """
        # Common transpositions
        transpositions = {
            "teh": "the",
            "taht": "that",
            "siad": "said",
            "thier": "their",
            "recieve": "receive",
            "freind": "friend",
            "dose": "does",
            "form": "from",
        }

        word_lower = word.lower()
        if word_lower in transpositions:
            corrected = transpositions[word_lower]
            # Preserve capitalization
            if word[0].isupper():
                corrected = corrected[0].upper() + corrected[1:]
            return corrected

        return word

    async def correct(
        self,
        text: str,
        user_id: str,
        use_cache: bool = True,
    ) -> list[Correction]:
        """Get quick corrections for text.

        Args:
            text: Input text to correct
            user_id: User ID (for personalization)
            use_cache: Whether to use cached results

        Returns:
            List of corrections
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text, user_id)
            if cache_key in self.cache:
                cached_result, cached_time = self.cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    logger.debug(f"Cache hit for user {user_id}")
                    return cached_result

        # Select session (personalized or base)
        session = self._get_user_session(user_id) or self.base_session

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="np",
            padding=True,
            truncation=True,
            max_length=128,
            return_offsets_mapping=True,
        )

        # Run inference
        try:
            start_time = time.perf_counter()

            outputs = session.run(
                None,
                {
                    "input_ids": inputs["input_ids"].astype(np.int64),
                    "attention_mask": inputs["attention_mask"].astype(np.int64),
                },
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"Inference took {elapsed_ms:.2f} ms")

            if elapsed_ms > 50:
                logger.warning(f"Inference exceeded 50ms target: {elapsed_ms:.2f} ms")

        except Exception as e:
            logger.error(f"ONNX inference failed: {e}", exc_info=True)
            return []

        # Decode predictions
        predictions: np.ndarray = outputs[0]  # type: ignore[assignment]  # Logits
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        offset_mapping = inputs["offset_mapping"][0]

        corrections = self._decode_predictions(
            text,
            predictions,
            tokens,
            offset_mapping,
        )

        # Cache result
        if use_cache:
            cache_key = self._get_cache_key(text, user_id)
            self.cache[cache_key] = (corrections, time.time())

        return corrections

    def _get_user_session(self, user_id: str) -> ort.InferenceSession | None:
        """Get personalized ONNX session for user.

        Args:
            user_id: User ID

        Returns:
            User session or None if not available
        """
        if user_id in self.user_sessions:
            return self.user_sessions[user_id]

        # Check for user adapter model
        user_model_path = Path(f"ml/models/adapters/{user_id}_v1.onnx")
        if user_model_path.exists():
            try:
                logger.info(f"Loading personalized model for user {user_id}")
                self.user_sessions[user_id] = ort.InferenceSession(
                    str(user_model_path),
                    providers=["CPUExecutionProvider"],
                )
                return self.user_sessions[user_id]
            except Exception as e:
                logger.error(f"Failed to load user model: {e}")

        return None

    def clear_cache(self) -> None:
        """Clear the correction cache."""
        self.cache.clear()
        logger.info("Cache cleared")


# Global service instance
_service_instance: QuickCorrectionService | None = None


def get_quick_correction_service() -> QuickCorrectionService | None:
    """Get or create Quick Correction Service instance.

    Returns:
        Service instance or None if model not available
    """
    global _service_instance

    if _service_instance is not None:
        return _service_instance

    # Try to load model
    model_path = Path("ml/models/quick_correction_base_v1")

    if not model_path.exists():
        logger.warning(f"Quick Correction model not found at {model_path}")
        logger.info("System will use Tier 2 (deep analysis) only")
        return None

    try:
        _service_instance = QuickCorrectionService(model_path)
        return _service_instance
    except Exception as e:
        logger.error(f"Failed to initialize Quick Correction Service: {e}")
        return None
