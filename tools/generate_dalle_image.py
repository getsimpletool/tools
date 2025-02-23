import warnings
# suppress pydantic warning which come from litellm -> pydantic/_internal/_config.py:345: UserWarning: Valid config keys have changed in V2:
warnings.filterwarnings("ignore")

from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, Sequence
from simpletool.types import TextContent, ImageContent, ErrorContent
from typing import Union, Optional
from litellm import image_generation


class InputModel(SimpleInputModel):
    """Input model for Dall-E image generation."""
    image_description: str = Field(
        description="Textual description of the image to generate",
        min_length=10,
        max_length=1000
    )
    model: str = Field(
        default="dall-e-3",
        description="The OpenAI DALL-E model to use"
    )
    size: str = Field(
        default="1024x1024",
        description="Size of the generated image",
        pattern=r'^\d+x\d+$'
    )
    quality: str = Field(
        default="standard",
        description="Quality of the generated image",
        pattern=r'^(standard|high)$'
    )
    n: int = Field(
        default=1,
        description="Number of images to generate",
        ge=1,
        le=10
    )
    env_vars: Optional[dict] = Field(
        default=None,
        description="Environment variables to set for the tool. ie: OPENAI_API_KEY, optionally OPENAI_BASE_URL",
        examples=[{"OPENAI_API_KEY": "sk-...", "OPENAI_BASE_URL": "https://api.openai.com/v1"}]
    )


class DallETool(SimpleTool):
    name = "generate_dalle_image"
    description = '''
    Generates images using OpenAI's Dall-E model.
    This tool is used to give the ability to generate images using the DALL-E model.
    It is a transformer-based model that generates images from textual descriptions.
    This tool allows to generate images based on the text input provided by the user.
    '''
    input_model = InputModel

    def __init__(self):
        super().__init__()
        self.env = {}

    def check_required_env(self, env: dict) -> str | None:
        if not env.get('OPENAI_API_KEY'):
            return "OpenAI API key is required. Please provide it in env_vars or set OPENAI_API_KEY environment variable."
        return None

    async def run(self, arguments: Dict[str, Any]) -> Sequence[Union[TextContent, ImageContent, ErrorContent]]:
        # Extract arguments with defaults
        arg = InputModel(**arguments)
        image_description = arg.image_description
        model = arg.model
        size = arg.size or "1024x1024"
        quality = arg.quality
        n = arg.n
        env_vars = arg.env_vars

        # Check environment variables
        self.env = self.get_env(env_vars or {})
        env_check = self.check_required_env(self.env)
        if env_check is not None:
            return [TextContent(type="text", text=str(env_check))]

        # Validate input
        if not image_description:
            return [TextContent(type="text", text="Missing required argument: image_description")]

        try:
            # Test mode
            if self.env.get('OPENAI_API_KEY') == "test":
                return [
                    ImageContent(
                        type="image",
                        mime_type="image/jpeg",
                        image="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                    )
                ]

            # Generate images
            response = image_generation(prompt=image_description,
                                        model=model,
                                        response_format="b64_json",
                                        n=n,
                                        size=size,
                                        quality=quality,
                                        api_key=self.env.get('OPENAI_API_KEY', None),
                                        base_url=self.env.get('OPENAI_BASE_URL', None)
                                        )

            if isinstance(response.data, list) and len(response.data) > 0:
                img = dict(response.data[0]).get("b64_json", None)
            else:
                return [TextContent(type="text", text="No images generated.")]

            return [
                ImageContent(
                    type="image",
                    mime_type="image/jpeg",
                    image=img,
                )
            ]

        except Exception as e:
            return [ErrorContent(code=500, error=f"Error generating image: {str(e)}"), ErrorContent(code=500, error="An error occurred")]
