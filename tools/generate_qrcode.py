import qrcode
from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, Sequence, Union
from simpletool.types import TextContent, ImageContent, ErrorContent
from io import BytesIO
from base64 import b64encode


class InputModel(SimpleInputModel):
    """Input model for QR code generation."""
    content: str = Field(
        description="The content to encode in the QR code",
        min_length=1,
        max_length=4296
    )
    scale: int = Field(
        default=5,
        description="Scale of the QR code image",
        ge=1,
        le=20
    )
    dark_color: str = Field(
        default="#000000",
        description="Color of the dark pixels in hex format"
    )
    light_color: str = Field(
        default="#FFFFFF",
        description="Color of the light pixels in hex format"
    )


class QRCodeTool(SimpleTool):
    name = "generate_qrcode"
    description = """
    Generates QR codes from text content.
    This tool uses the qrcode library to create QR codes that can encode various types of data.
    """
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> Sequence[Union[ImageContent, TextContent, ErrorContent]]:
        # Extract arguments with defaults
        try:
            arg = InputModel(**arguments)
        except Exception as e:
            return [ErrorContent(code=400, error=f"Invalid arguments: {str(e)}")]

        content = arg.content
        scale = arg.scale
        dark_color = arg.dark_color
        light_color = arg.light_color

        if not content:
            return [ErrorContent(code=400, error="Missing required argument: content")]

        try:
            # Validate input
            qr = qrcode.QRCode(version=1, box_size=scale, border=4)
            qr.add_data(content)
            qr.make(fit=True)

            # Create an image from the QR Code
            img = qr.make_image(fill_color=dark_color, back_color=light_color)

            # Save to BytesIO
            buffer = BytesIO()
            img.save(buffer)
            buffer.seek(0)

            # Convert to base64
            base64_img = b64encode(buffer.getvalue()).decode('utf-8')

            # Return as ImageContent
            return [ImageContent(
                type="image",
                image=base64_img,
                mime_type="image/png"
            )]

        except Exception as e:
            return [ErrorContent(code=500, error=f"Error generating QR code: {str(e)}")]
