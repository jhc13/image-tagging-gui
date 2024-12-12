import numpy as np
import torch
from transformers import LlavaForConditionalGeneration, BatchFeature

from auto_captioning import captioning_thread
from auto_captioning.auto_captioning_model import AutoCaptioningModel
from utils.image import Image


class Joycaption(AutoCaptioningModel):
    dtype = torch.bfloat16
    transformers_model_class = LlavaForConditionalGeneration

    def __init__(self,
                 captioning_thread_: 'captioning_thread.CaptioningThread',
                 caption_settings: dict):
        super().__init__(captioning_thread_, caption_settings)

        self.input_length = None
        self.dtype_argument = ({'dtype': self.dtype}
                               if self.device.type == 'cuda' else {})

    def get_additional_error_message(self) -> str | None:
        if self.load_in_4_bit:
            return 'This model cannot be loaded in 4-bit.'
        return None

    @staticmethod
    def get_default_prompt() -> str:
        return 'Write a stable diffusion prompt for this image.'

    def format_prompt(self, prompt: str) -> str:
        conversation = [
            {
                'role': 'system',
                'content': 'You are a helpful image captioner.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        templated_prompt = self.processor.apply_chat_template(
            conversation, tokenize=False, add_generation_prompt=True)
        return templated_prompt

    def get_input_text(self, image_prompt: str) -> str:
        return image_prompt + self.caption_start

    def get_model_inputs(self, image_prompt: str,
                         image: Image) -> BatchFeature | dict | np.ndarray:
        model_inputs = super().get_model_inputs(image_prompt, image)
        # Cache our input token length so we can remove that many from the
        # model's response.
        self.input_length = model_inputs['input_ids'].shape[1]
        return model_inputs

    def get_caption_from_generated_tokens(
            self, generated_token_ids: torch.Tensor, image_prompt: str) -> str:
        # Remove our prompt from the generated result
        generated_token_ids = generated_token_ids[:, self.input_length:]
        return super().get_caption_from_generated_tokens(
            generated_token_ids, image_prompt)